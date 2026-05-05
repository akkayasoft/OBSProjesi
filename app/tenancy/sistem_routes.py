"""Platform admin (sistem) UI route'lari — /sistem/ prefix'inde.

Tenant'lardan tamamen bagimsiz; master DB'de yasayan PlatformAdmin
hesaplariyla giris yapilir. Tum tenant'lari toplu yonetmek, yeni
dershane eklemek, plan/limit duzenlemek, askiya almak icin.
"""
from __future__ import annotations

import os
import subprocess
import sys
from contextlib import contextmanager
from datetime import datetime
from urllib.parse import urlparse

from flask import (Blueprint, render_template, redirect, url_for, flash,
                    request, abort, current_app)
from sqlalchemy import or_, func, text
from sqlalchemy.orm import Session as SAQSession

from app.tenancy.master import master_session, get_master_engine
from app.tenancy.models import (Tenant, PlatformAdmin, PlatformAuditLog,
                                ImpersonationToken)
from app.tenancy.limitler import PLAN_LIMITLERI
from app.tenancy.sistem_auth import (
    aktif_platform_admin, platform_admin_login, platform_admin_logout,
    platform_admin_required, audit_kaydet,
)


bp = Blueprint('sistem', __name__, url_prefix='/sistem')


# === Yardimcilar ===

ROLLER_LISTESI = ['yonetici', 'ogretmen', 'muhasebeci', 'veli', 'ogrenci']

KURUM_TIPLERI = [
    ('dershane',     'Dershane / Okul (OBS)'),
    ('surucu_kursu', 'Sürücü Kursu'),
]
KURUM_TIPI_DICT = dict(KURUM_TIPLERI)


def _slugify(s: str) -> str:
    out = []
    for ch in (s or '').lower():
        if ch.isalnum() or ch == '-':
            out.append(ch)
        elif ch in (' ', '_'):
            out.append('-')
    # Turkce karakterler
    tr_map = {'ı': 'i', 'ş': 's', 'ğ': 'g', 'ü': 'u', 'ö': 'o', 'ç': 'c'}
    s2 = ''.join(out)
    for tr, en in tr_map.items():
        s2 = s2.replace(tr, en)
    return s2.strip('-') or 'tenant'


def _default_db_name(slug: str) -> str:
    return 'obs_' + slug.replace('-', '_')


@contextmanager
def _tenant_session(db_name: str):
    """Tenant DB'si uzerinde kisa omurlu raw SQLAlchemy session."""
    from app.tenancy.engines import get_tenant_engine
    engine = get_tenant_engine(db_name)
    s = SAQSession(engine, future=True, expire_on_commit=False)
    try:
        yield s
    finally:
        s.close()


def _safe_next(url: str | None) -> str | None:
    """Open-redirect'e karsi: sadece ayni site path'ine izin ver."""
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.netloc:
        return None
    if not parsed.path.startswith('/sistem/'):
        return None
    return url


# === Auth ===

@bp.route('/giris', methods=['GET', 'POST'])
def giris():
    # Zaten giris yapildiysa dashboard'a
    if aktif_platform_admin():
        return redirect(url_for('sistem.dashboard'))

    hata = None
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        sifre = request.form.get('password') or ''

        with master_session() as s:
            admin = s.query(PlatformAdmin).filter(
                func.lower(PlatformAdmin.username) == username.lower(),
                PlatformAdmin.aktif.is_(True),
            ).first()
            if admin and admin.check_password(sifre):
                admin.son_giris = datetime.utcnow()
                audit_kaydet(s, admin, 'login')
                s.commit()
                platform_admin_login(admin)
                hedef = _safe_next(request.args.get('next')) or url_for('sistem.dashboard')
                return redirect(hedef)
            hata = 'Kullanici adi veya sifre hatali.'

    return render_template('sistem/giris.html', hata=hata)


@bp.route('/cikis', methods=['POST'])
def cikis():
    admin = aktif_platform_admin()
    if admin:
        with master_session() as s:
            audit_kaydet(s, admin, 'logout')
            s.commit()
    platform_admin_logout()
    return redirect(url_for('sistem.giris'))


# === Dashboard ===

@bp.route('/')
@platform_admin_required
def dashboard():
    arama = (request.args.get('arama') or '').strip()
    durum = (request.args.get('durum') or '').strip()

    with master_session() as s:
        q = s.query(Tenant)
        if durum:
            q = q.filter(Tenant.durum == durum)
        if arama:
            like = f'%{arama}%'
            q = q.filter(or_(
                Tenant.slug.ilike(like),
                Tenant.ad.ilike(like),
                Tenant.iletisim_email.ilike(like),
            ))
        tenants = q.order_by(Tenant.created_at.desc()).all()
        for t in tenants:
            s.expunge(t)

        # Ozet sayilari
        toplam = s.query(func.count(Tenant.id)).scalar() or 0
        aktif = s.query(func.count(Tenant.id)).filter(Tenant.durum == 'aktif').scalar() or 0
        askida = s.query(func.count(Tenant.id)).filter(Tenant.durum == 'askida').scalar() or 0

    return render_template(
        'sistem/dashboard.html',
        tenants=tenants,
        toplam=toplam,
        aktif=aktif,
        askida=askida,
        arama=arama,
        durum=durum,
        planlar=PLAN_LIMITLERI,
    )


# === Yeni tenant olustur (UI) ===

@bp.route('/tenant/yeni', methods=['GET', 'POST'])
@platform_admin_required
def tenant_yeni():
    hata = None
    form_data = {
        'ad': '', 'slug': '', 'iletisim_email': '', 'plan': 'standart',
        'yonetici_username': '', 'yonetici_ad': '', 'yonetici_soyad': '',
        'yonetici_email': '',
    }
    form_data['kurum_tipi'] = 'dershane'
    if request.method == 'POST':
        form_data['ad'] = (request.form.get('ad') or '').strip()
        slug_raw = (request.form.get('slug') or '').strip()
        form_data['slug'] = _slugify(slug_raw or form_data['ad'])
        form_data['iletisim_email'] = (request.form.get('iletisim_email') or '').strip()
        form_data['plan'] = (request.form.get('plan') or 'standart').strip()
        form_data['kurum_tipi'] = (request.form.get('kurum_tipi') or 'dershane').strip()
        if form_data['kurum_tipi'] not in KURUM_TIPI_DICT:
            form_data['kurum_tipi'] = 'dershane'
        form_data['yonetici_username'] = (request.form.get('yonetici_username') or '').strip()
        form_data['yonetici_ad'] = (request.form.get('yonetici_ad') or '').strip()
        form_data['yonetici_soyad'] = (request.form.get('yonetici_soyad') or '').strip()
        form_data['yonetici_email'] = (request.form.get('yonetici_email') or '').strip()
        yonetici_sifre = request.form.get('yonetici_sifre') or ''

        # Validasyon
        if not form_data['ad']:
            hata = 'Kurum adı zorunludur.'
        elif not form_data['slug']:
            hata = 'Slug üretilemedi — adı tekrar deneyin veya elle girin.'
        elif form_data['plan'] not in PLAN_LIMITLERI:
            hata = 'Geçersiz plan seçildi.'
        elif not form_data['yonetici_username']:
            hata = 'Yönetici kullanıcı adı zorunludur.'
        elif len(yonetici_sifre) < 6:
            hata = 'Yönetici şifresi en az 6 karakter olmalı.'
        elif not form_data['yonetici_ad'] or not form_data['yonetici_soyad']:
            hata = 'Yönetici adı ve soyadı zorunludur.'

        if hata:
            return render_template('sistem/tenant_yeni.html',
                                   hata=hata, form=form_data,
                                   planlar=PLAN_LIMITLERI,
                                   kurum_tipler=KURUM_TIPLERI)

        slug = form_data['slug']
        db_name = _default_db_name(slug)
        admin = aktif_platform_admin()

        # 1) Master DB'de slug benzersizligi
        with master_session() as s:
            if s.query(Tenant).filter_by(slug=slug).first():
                return render_template('sistem/tenant_yeni.html',
                                       hata=f'Bu slug zaten kullanımda: {slug}',
                                       form=form_data, planlar=PLAN_LIMITLERI,
                                       kurum_tipler=KURUM_TIPLERI)
            if s.query(Tenant).filter_by(db_name=db_name).first():
                return render_template('sistem/tenant_yeni.html',
                                       hata=f'Bu DB adı zaten kullanımda: {db_name}',
                                       form=form_data, planlar=PLAN_LIMITLERI,
                                       kurum_tipler=KURUM_TIPLERI)

        # 2) Postgres'te CREATE DATABASE
        try:
            admin_engine = get_master_engine()
            with admin_engine.connect() as conn:
                conn.execute(text('COMMIT'))  # autocommit
                exists = conn.execute(
                    text('SELECT 1 FROM pg_database WHERE datname=:n'),
                    {'n': db_name},
                ).first()
                if not exists:
                    conn.execute(text(f'CREATE DATABASE "{db_name}"'))
        except Exception as e:
            return render_template('sistem/tenant_yeni.html',
                                   hata=f'DB oluşturulamadı: {e}',
                                   form=form_data, planlar=PLAN_LIMITLERI,
                                   kurum_tipler=KURUM_TIPLERI)

        # 3) Migration: subprocess ile flask db upgrade
        from app.tenancy.engines import _build_url
        url = _build_url(db_name)
        env = os.environ.copy()
        env['DATABASE_URL'] = url
        env['MULTITENANT_ENABLED'] = '0'
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'db', 'upgrade'],
            env=env, capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            return render_template(
                'sistem/tenant_yeni.html',
                hata=('Migration başarısız:\n' +
                      (result.stderr or result.stdout or '')[:1500]),
                form=form_data, planlar=PLAN_LIMITLERI,
                kurum_tipler=KURUM_TIPLERI,
            )

        # 3.5) Modele eklenmis ama Alembic migrasyonu yazilmamis kolonlari
        #      yeni tenant'a uygula (idempotent). Aksi takdirde / route'unda
        #      'column ... does not exist' hatasi verir.
        try:
            from app.tenancy.engines import get_tenant_engine
            from app.tenancy.cli import tenant_kolonlarini_backfill_et
            yeni_engine = get_tenant_engine(db_name)
            tenant_kolonlarini_backfill_et(
                yeni_engine,
                surucu_kursu=(form_data['kurum_tipi'] == 'surucu_kursu'),
            )
        except Exception as e:
            current_app.logger.warning(
                f'tenant_yeni backfill basarisiz ({db_name}): {e}'
            )

        # 4) Master DB'ye Tenant kaydi
        with master_session() as s:
            t = Tenant(
                slug=slug, ad=form_data['ad'], db_name=db_name,
                durum='aktif', plan=form_data['plan'],
                kurum_tipi=form_data['kurum_tipi'],
                iletisim_email=form_data['iletisim_email'] or None,
            )
            s.add(t)
            s.flush()
            audit_kaydet(
                s, admin, 'tenant_create', tenant=t,
                detay=(f'plan={form_data["plan"]} '
                       f'tip={form_data["kurum_tipi"]} db={db_name}'),
            )
            s.commit()
            tenant_id = t.id

        # 5) Tenant DB'sine ilk yonetici kullaniciyi ekle (+ tum modul izinleri)
        try:
            from app.models.user import User
            from app.models.ayarlar import RolModulIzin, KullaniciModulIzin
            with _tenant_session(db_name) as ts:
                yu = User(
                    username=form_data['yonetici_username'],
                    email=form_data['yonetici_email'] or
                          f'{form_data["yonetici_username"]}@{slug}.obs',
                    ad=form_data['yonetici_ad'],
                    soyad=form_data['yonetici_soyad'],
                    rol='yonetici',
                    aktif=True,
                )
                yu.set_password(yonetici_sifre)
                ts.add(yu)
                ts.flush()
                # Tum modullere izin ver
                for modul_key in RolModulIzin.MODULLER.keys():
                    ts.add(KullaniciModulIzin(
                        user_id=yu.id, modul_key=modul_key, aktif=True,
                    ))
                ts.commit()
        except Exception as e:
            flash(f'Tenant oluşturuldu, ancak yönetici eklenemedi: {e}', 'warning')
            return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))

        flash(f'"{form_data["ad"]}" başarıyla oluşturuldu. '
              f'Yönetici girişi: {form_data["yonetici_username"]}', 'success')
        return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))

    return render_template('sistem/tenant_yeni.html',
                           hata=None, form=form_data,
                           planlar=PLAN_LIMITLERI,
                           kurum_tipler=KURUM_TIPLERI)


# === Tenant detay & duzenleme ===

@bp.route('/tenant/<int:tenant_id>')
@platform_admin_required
def tenant_detay(tenant_id):
    with master_session() as s:
        tenant = s.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            abort(404)
        s.expunge(tenant)

        # Audit log son 20 kayit
        loglar = (s.query(PlatformAuditLog)
                  .filter(PlatformAuditLog.tenant_id == tenant_id)
                  .order_by(PlatformAuditLog.created_at.desc())
                  .limit(20).all())
        for l in loglar:
            s.expunge(l)

    # Tenant'in DB'sinden istatistik (best-effort)
    istatistik = _tenant_istatistik(tenant.db_name)

    return render_template(
        'sistem/tenant_detay.html',
        tenant=tenant,
        loglar=loglar,
        istatistik=istatistik,
        planlar=PLAN_LIMITLERI,
    )


def _tenant_istatistik(db_name: str) -> dict:
    """Tenant'in kendi DB'sinden ogrenci/ogretmen/kullanici sayisini cek.

    Hata olursa boş dict dondur — sayfa render olmaya devam etsin.
    """
    try:
        from app.tenancy.engines import get_tenant_engine
        from sqlalchemy.orm import Session as SAQSession
        from app.models.user import User
        from app.models.muhasebe import Ogrenci

        engine = get_tenant_engine(db_name)
        with SAQSession(engine) as ss:
            ogrenci = ss.query(func.count(Ogrenci.id)).filter(Ogrenci.aktif.is_(True)).scalar() or 0
            ogretmen = ss.query(func.count(User.id)).filter(
                User.rol == 'ogretmen', User.aktif.is_(True)
            ).scalar() or 0
            kullanici = ss.query(func.count(User.id)).filter(User.aktif.is_(True)).scalar() or 0
        return {'ogrenci': ogrenci, 'ogretmen': ogretmen, 'kullanici': kullanici}
    except Exception:
        return {}


@bp.route('/tenant/<int:tenant_id>/duzenle', methods=['POST'])
@platform_admin_required
def tenant_duzenle(tenant_id):
    yeni_plan = (request.form.get('plan') or '').strip()
    if yeni_plan not in PLAN_LIMITLERI:
        flash('Geçersiz plan.', 'danger')
        return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))

    def _int_or_none(key):
        v = (request.form.get(key) or '').strip()
        if v == '':
            return None
        try:
            return max(0, int(v))
        except ValueError:
            return None

    yeni_ogrenci = _int_or_none('ogrenci_limiti')
    yeni_ogretmen = _int_or_none('ogretmen_limiti')
    yeni_kullanici = _int_or_none('kullanici_limiti')
    iletisim_email = (request.form.get('iletisim_email') or '').strip() or None
    iletisim_telefon = (request.form.get('iletisim_telefon') or '').strip() or None
    abonelik_bitis_str = (request.form.get('abonelik_bitis') or '').strip()
    abonelik_bitis = None
    if abonelik_bitis_str:
        try:
            from datetime import date
            abonelik_bitis = date.fromisoformat(abonelik_bitis_str)
        except ValueError:
            pass

    admin = aktif_platform_admin()
    with master_session() as s:
        tenant = s.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            abort(404)
        eski_plan = tenant.plan
        tenant.plan = yeni_plan
        tenant.ogrenci_limiti = yeni_ogrenci
        tenant.ogretmen_limiti = yeni_ogretmen
        tenant.kullanici_limiti = yeni_kullanici
        tenant.iletisim_email = iletisim_email
        tenant.iletisim_telefon = iletisim_telefon
        tenant.abonelik_bitis = abonelik_bitis
        audit_kaydet(s, admin, 'tenant_update', tenant=tenant,
                      detay=f'plan: {eski_plan} -> {yeni_plan}, '
                            f'ogrenci_limit={yeni_ogrenci}, '
                            f'ogretmen_limit={yeni_ogretmen}, '
                            f'kullanici_limit={yeni_kullanici}')
        s.commit()
    flash('Tenant bilgileri güncellendi.', 'success')
    return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))


@bp.route('/tenant/<int:tenant_id>/durum', methods=['POST'])
@platform_admin_required
def tenant_durum(tenant_id):
    yeni_durum = (request.form.get('durum') or '').strip()
    if yeni_durum not in ('aktif', 'askida'):
        abort(400)
    admin = aktif_platform_admin()
    with master_session() as s:
        tenant = s.query(Tenant).filter_by(id=tenant_id).first()
        if not tenant:
            abort(404)
        eski = tenant.durum
        tenant.durum = yeni_durum
        audit_kaydet(s, admin,
                     'tenant_suspend' if yeni_durum == 'askida' else 'tenant_activate',
                     tenant=tenant,
                     detay=f'{eski} -> {yeni_durum}')
        s.commit()
        slug = tenant.slug
        ad = tenant.ad
    flash(f'"{ad}" durumu "{yeni_durum}" olarak güncellendi.', 'success')
    return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))


# === Tenant kullanici yonetimi (cross-tenant) ===

def _tenant_yukle(tenant_id: int):
    """Master DB'den tenant'i detached olarak yukle."""
    with master_session() as s:
        t = s.query(Tenant).filter_by(id=tenant_id).first()
        if not t:
            return None
        s.expunge(t)
        return t


@bp.route('/tenant/<int:tenant_id>/kullanici/')
@platform_admin_required
def tenant_kullanicilar(tenant_id):
    tenant = _tenant_yukle(tenant_id)
    if not tenant:
        abort(404)

    arama = (request.args.get('arama') or '').strip()
    rol = (request.args.get('rol') or '').strip()
    kullanicilar = []
    hata = None
    try:
        from app.models.user import User
        with _tenant_session(tenant.db_name) as ts:
            q = ts.query(User)
            if rol:
                q = q.filter(User.rol == rol)
            if arama:
                like = f'%{arama}%'
                q = q.filter(or_(
                    User.username.ilike(like),
                    User.ad.ilike(like),
                    User.soyad.ilike(like),
                    User.email.ilike(like),
                ))
            kullanicilar = q.order_by(User.id.desc()).all()
            for u in kullanicilar:
                ts.expunge(u)
    except Exception as e:
        hata = f'Kullanıcılar yüklenemedi: {e}'

    return render_template(
        'sistem/tenant_kullanicilar.html',
        tenant=tenant, kullanicilar=kullanicilar,
        arama=arama, rol=rol, hata=hata,
        roller=ROLLER_LISTESI,
    )


@bp.route('/tenant/<int:tenant_id>/kullanici/yeni', methods=['POST'])
@platform_admin_required
def tenant_kullanici_yeni(tenant_id):
    tenant = _tenant_yukle(tenant_id)
    if not tenant:
        abort(404)

    username = (request.form.get('username') or '').strip()
    ad = (request.form.get('ad') or '').strip()
    soyad = (request.form.get('soyad') or '').strip()
    email = (request.form.get('email') or '').strip()
    rol = (request.form.get('rol') or 'muhasebeci').strip()
    sifre = request.form.get('sifre') or ''

    if not username or not ad or not soyad or len(sifre) < 6:
        flash('Tüm alanlar zorunlu, şifre en az 6 karakter olmalı.', 'danger')
        return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))
    if rol not in ROLLER_LISTESI + ['admin']:
        flash('Geçersiz rol.', 'danger')
        return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))

    admin = aktif_platform_admin()
    try:
        from app.models.user import User
        from app.models.ayarlar import RolModulIzin, KullaniciModulIzin
        with _tenant_session(tenant.db_name) as ts:
            mevcut = ts.query(User).filter(
                or_(User.username == username,
                    User.email == (email or f'{username}@{tenant.slug}.obs'))
            ).first()
            if mevcut:
                flash('Bu kullanıcı adı veya e-posta zaten kullanımda.', 'danger')
                return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))

            u = User(
                username=username, ad=ad, soyad=soyad,
                email=email or f'{username}@{tenant.slug}.obs',
                rol=rol, aktif=True,
            )
            u.set_password(sifre)
            ts.add(u)
            ts.flush()
            # yonetici icin tum modullere izin
            if rol == 'yonetici':
                for modul_key in RolModulIzin.MODULLER.keys():
                    ts.add(KullaniciModulIzin(
                        user_id=u.id, modul_key=modul_key, aktif=True,
                    ))
            ts.commit()
    except Exception as e:
        flash(f'Kullanıcı eklenemedi: {e}', 'danger')
        return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))

    with master_session() as s:
        t = s.query(Tenant).filter_by(id=tenant_id).first()
        audit_kaydet(s, admin, 'tenant_user_create', tenant=t,
                     detay=f'username={username} rol={rol}')
        s.commit()

    flash(f'"{username}" eklendi.', 'success')
    return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))


@bp.route('/tenant/<int:tenant_id>/kullanici/<int:user_id>/sifre', methods=['POST'])
@platform_admin_required
def tenant_kullanici_sifre(tenant_id, user_id):
    tenant = _tenant_yukle(tenant_id)
    if not tenant:
        abort(404)

    yeni_sifre = request.form.get('yeni_sifre') or ''
    if len(yeni_sifre) < 6:
        flash('Şifre en az 6 karakter olmalı.', 'danger')
        return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))

    admin = aktif_platform_admin()
    try:
        from app.models.user import User
        with _tenant_session(tenant.db_name) as ts:
            u = ts.query(User).filter_by(id=user_id).first()
            if not u:
                abort(404)
            u.set_password(yeni_sifre)
            ts.commit()
            kullanici_adi = u.username
    except Exception as e:
        flash(f'Şifre güncellenemedi: {e}', 'danger')
        return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))

    with master_session() as s:
        t = s.query(Tenant).filter_by(id=tenant_id).first()
        audit_kaydet(s, admin, 'tenant_user_password_reset', tenant=t,
                     detay=f'user_id={user_id} username={kullanici_adi}')
        s.commit()
    flash(f'"{kullanici_adi}" şifresi güncellendi.', 'success')
    return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))


@bp.route('/tenant/<int:tenant_id>/kullanici/<int:user_id>/durum', methods=['POST'])
@platform_admin_required
def tenant_kullanici_durum(tenant_id, user_id):
    tenant = _tenant_yukle(tenant_id)
    if not tenant:
        abort(404)

    admin = aktif_platform_admin()
    try:
        from app.models.user import User
        with _tenant_session(tenant.db_name) as ts:
            u = ts.query(User).filter_by(id=user_id).first()
            if not u:
                abort(404)
            u.aktif = not u.aktif
            ts.commit()
            kullanici_adi = u.username
            yeni_aktif = u.aktif
    except Exception as e:
        flash(f'Durum güncellenemedi: {e}', 'danger')
        return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))

    with master_session() as s:
        t = s.query(Tenant).filter_by(id=tenant_id).first()
        audit_kaydet(s, admin, 'tenant_user_toggle', tenant=t,
                     detay=f'user_id={user_id} username={kullanici_adi} aktif={yeni_aktif}')
        s.commit()
    flash(f'"{kullanici_adi}" {"aktifleştirildi" if yeni_aktif else "pasifleştirildi"}.',
          'success')
    return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))


@bp.route('/tenant/<int:tenant_id>/kullanici/<int:user_id>/sil', methods=['POST'])
@platform_admin_required
def tenant_kullanici_sil(tenant_id, user_id):
    tenant = _tenant_yukle(tenant_id)
    if not tenant:
        abort(404)

    admin = aktif_platform_admin()
    try:
        from app.models.user import User
        with _tenant_session(tenant.db_name) as ts:
            u = ts.query(User).filter_by(id=user_id).first()
            if not u:
                abort(404)
            kullanici_adi = u.username
            rol = u.rol
            # Son admin/yoneticiyi silmeyi engelle
            if rol in ('admin', 'yonetici'):
                kalan = ts.query(func.count(User.id)).filter(
                    User.rol.in_(['admin', 'yonetici']),
                    User.aktif.is_(True),
                    User.id != user_id,
                ).scalar() or 0
                if kalan == 0:
                    flash('Son admin/yönetici silinemez. Önce başka bir admin '
                          'kullanıcı oluşturun.', 'danger')
                    return redirect(url_for('sistem.tenant_kullanicilar',
                                             tenant_id=tenant_id))
            ts.delete(u)
            ts.commit()
    except Exception as e:
        flash(f'Kullanıcı silinemedi: {e}', 'danger')
        return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))

    with master_session() as s:
        t = s.query(Tenant).filter_by(id=tenant_id).first()
        audit_kaydet(s, admin, 'tenant_user_delete', tenant=t,
                     detay=f'user_id={user_id} username={kullanici_adi}')
        s.commit()
    flash(f'"{kullanici_adi}" silindi.', 'success')
    return redirect(url_for('sistem.tenant_kullanicilar', tenant_id=tenant_id))


# === Impersonate (gecici yonetici girisi) ===

def _impersonate_serializer():
    from itsdangerous import URLSafeTimedSerializer
    secret = current_app.config['SECRET_KEY']
    return URLSafeTimedSerializer(secret, salt='sistem-impersonate-v1')


@bp.route('/tenant/<int:tenant_id>/impersonate', methods=['POST'])
@platform_admin_required
def tenant_impersonate(tenant_id):
    """Tenant'in yonetici hesabina gecici giris token'i uretir, tenant
    subdomain'ine yonlendirir. Tenant tarafi /auth/impersonate?t=...
    endpoint'i ile token'i tuketir.

    Token kisa omurlu (2 dk) ve tek kullanimliktir (master DB'de
    tuketildi flag'i ile track edilir).
    """
    tenant = _tenant_yukle(tenant_id)
    if not tenant:
        abort(404)
    if tenant.durum != 'aktif':
        flash('Askıya alınmış tenant\'a impersonate yapılamaz.', 'danger')
        return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))

    target_user_id = (request.form.get('user_id') or '').strip()
    admin = aktif_platform_admin()

    try:
        from app.models.user import User
        with _tenant_session(tenant.db_name) as ts:
            q = ts.query(User).filter(
                User.aktif.is_(True),
                User.rol.in_(['admin', 'yonetici']),
            )
            if target_user_id:
                try:
                    q = q.filter(User.id == int(target_user_id))
                except ValueError:
                    pass
            target = q.order_by(User.id.asc()).first()
            if not target:
                flash('Tenant\'ta impersonate edilebilecek admin/yönetici '
                      'kullanıcı yok.', 'danger')
                return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))
            target_id = target.id
            target_username = target.username
    except Exception as e:
        flash(f'Tenant DB\'sine ulaşılamadı: {e}', 'danger')
        return redirect(url_for('sistem.tenant_detay', tenant_id=tenant_id))

    # Token uret — jti (unique id) ile birlikte tek kullanimlik
    import uuid
    jti = uuid.uuid4().hex
    s_token = _impersonate_serializer()
    token = s_token.dumps({
        'tenant_slug': tenant.slug,
        'user_id': target_id,
        'admin_username': admin.username if admin else None,
        'jti': jti,
    })

    # Master DB'ye token kaydi (kullanildi_mi=False) + audit
    with master_session() as s:
        t = s.query(Tenant).filter_by(id=tenant_id).first()
        s.add(ImpersonationToken(
            jti=jti,
            tenant_id=tenant_id,
            tenant_slug=tenant.slug,
            target_user_id=target_id,
            target_username=target_username,
            admin_id=admin.id if admin else None,
            admin_username=admin.username if admin else None,
            kullanildi_mi=False,
        ))
        audit_kaydet(s, admin, 'tenant_impersonate_issue', tenant=t,
                     detay=f'target_user={target_username} (id={target_id}) jti={jti[:8]}')
        s.commit()

    # Tenant subdomain URL'ini hesapla
    base = current_app.config.get('TENANT_ROOT_DOMAIN') or \
        current_app.config.get('TENANT_URL_BASE')
    if base:
        # Ornek: 'obs.akkayasoft.com' -> https://<slug>.obs.akkayasoft.com
        scheme = 'http' if base.startswith(('localhost', '127.0.0.1')) else 'https'
        target_url = f'{scheme}://{tenant.slug}.{base}/auth/impersonate?t={token}'
    else:
        # Fallback: ayni domain'de path-based (gelistirme)
        target_url = url_for('auth.impersonate_consume', _external=True) + f'?t={token}'

    return redirect(target_url)


# === Audit log ===

@bp.route('/audit')
@platform_admin_required
def audit():
    sayfa = request.args.get('sayfa', 1, type=int)
    LIMIT = 50
    with master_session() as s:
        q = (s.query(PlatformAuditLog)
             .order_by(PlatformAuditLog.created_at.desc()))
        toplam = q.count()
        loglar = q.offset((sayfa - 1) * LIMIT).limit(LIMIT).all()
        for l in loglar:
            s.expunge(l)
    son_sayfa = max(1, (toplam + LIMIT - 1) // LIMIT)
    return render_template('sistem/audit.html',
                           loglar=loglar,
                           sayfa=sayfa,
                           son_sayfa=son_sayfa,
                           toplam=toplam)
