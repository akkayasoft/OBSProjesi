"""Dershane Yoneticisi yonetim route'lari.

Sadece 'admin' rolu bu ekranlara erisebilir. Yonetici baska yoneticiyi
yonetemez (role_required('admin') tek basina kalir, yonetici decorator
uzerinden gecemez cunku URL /kullanici ve kullanici module yonetici
varsayilan preset'lerinde yok).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.user import User
from app.models.ayarlar import RolModulIzin, KullaniciModulIzin
from app.module_registry import PRESETLER, preset_moduller
from app.kullanici.forms import YoneticiForm, YoneticiDuzenleForm


bp = Blueprint('yonetici', __name__, url_prefix='/yonetici')


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    arama = request.args.get('arama', '').strip()

    query = User.query.filter_by(rol='yonetici')
    if arama:
        arama_pattern = f'%{arama}%'
        query = query.filter(
            db.or_(
                User.username.ilike(arama_pattern),
                User.ad.ilike(arama_pattern),
                User.soyad.ilike(arama_pattern),
                User.email.ilike(arama_pattern),
            )
        )

    yoneticiler = query.order_by(User.olusturma_tarihi.desc()).paginate(
        page=page, per_page=20
    )

    # Her yonetici icin izinli modul sayisini hesapla (tek sorgu ile)
    izin_sayilari = {}
    if yoneticiler.items:
        ids = [y.id for y in yoneticiler.items]
        kayitlar = KullaniciModulIzin.query.filter(
            KullaniciModulIzin.user_id.in_(ids),
            KullaniciModulIzin.aktif.is_(True),
        ).all()
        for k in kayitlar:
            izin_sayilari[k.user_id] = izin_sayilari.get(k.user_id, 0) + 1

    return render_template(
        'kullanici/yonetici_liste.html',
        yoneticiler=yoneticiler,
        arama=arama,
        izin_sayilari=izin_sayilari,
        toplam_modul=len(RolModulIzin.MODULLER),
    )


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = YoneticiForm()

    if form.validate_on_submit():
        # Kullanici olustur
        yonetici = User(
            username=form.username.data,
            email=form.email.data,
            ad=form.ad.data,
            soyad=form.soyad.data,
            rol='yonetici',
            aktif=form.aktif.data,
        )
        yonetici.set_password(form.password.data)
        db.session.add(yonetici)
        db.session.flush()  # id'yi almak icin

        # Preset veya ozel modul secimini oku
        preset_key = form.preset.data
        if preset_key == 'ozel':
            # Ozel secim: POST'taki checkbox'lardan al
            secilen_moduller = request.form.getlist('moduller')
        else:
            secilen_moduller = preset_moduller(preset_key)

        KullaniciModulIzin.kullanici_izinlerini_ayarla(yonetici.id, secilen_moduller)
        db.session.commit()

        flash(f'{yonetici.tam_ad} dershane yoneticisi olusturuldu. '
              f'({len(secilen_moduller)} modul izni verildi)', 'success')
        return redirect(url_for('kullanici.yonetici.liste'))

    return render_template(
        'kullanici/yonetici_form.html',
        form=form,
        moduller=RolModulIzin.MODULLER,
        presetler=PRESETLER,
        mevcut_izinler=set(),  # Yeni kayit, hic bir sey secili degil
        mod='yeni',
    )


@bp.route('/<int:kullanici_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(kullanici_id):
    yonetici = User.query.filter_by(id=kullanici_id, rol='yonetici').first_or_404()
    form = YoneticiDuzenleForm(kullanici_id=yonetici.id, obj=yonetici)

    if form.validate_on_submit():
        yonetici.username = form.username.data
        yonetici.email = form.email.data
        yonetici.ad = form.ad.data
        yonetici.soyad = form.soyad.data
        yonetici.aktif = form.aktif.data
        if form.password.data:
            yonetici.set_password(form.password.data)

        # Modul izinlerini POST'tan al (checkbox listesi)
        secilen_moduller = request.form.getlist('moduller')
        KullaniciModulIzin.kullanici_izinlerini_ayarla(yonetici.id, secilen_moduller)
        db.session.commit()

        flash(f'{yonetici.tam_ad} guncellendi. ({len(secilen_moduller)} modul izni)', 'success')
        return redirect(url_for('kullanici.yonetici.liste'))

    mevcut_izinler = KullaniciModulIzin.kullanici_izinleri(yonetici.id)

    return render_template(
        'kullanici/yonetici_form.html',
        form=form,
        yonetici=yonetici,
        moduller=RolModulIzin.MODULLER,
        presetler=PRESETLER,
        mevcut_izinler=mevcut_izinler,
        mod='duzenle',
    )


@bp.route('/<int:kullanici_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(kullanici_id):
    yonetici = User.query.filter_by(id=kullanici_id, rol='yonetici').first_or_404()
    ad = yonetici.tam_ad
    db.session.delete(yonetici)  # cascade ile modul izinleri de silinir
    db.session.commit()
    flash(f'{ad} silindi.', 'success')
    return redirect(url_for('kullanici.yonetici.liste'))


@bp.route('/<int:kullanici_id>/aktif-toggle', methods=['POST'])
@login_required
@role_required('admin')
def aktif_toggle(kullanici_id):
    yonetici = User.query.filter_by(id=kullanici_id, rol='yonetici').first_or_404()
    yonetici.aktif = not yonetici.aktif
    db.session.commit()
    durum = 'aktif' if yonetici.aktif else 'pasif'
    flash(f'{yonetici.tam_ad} {durum} yapildi.', 'success')
    return redirect(url_for('kullanici.yonetici.liste'))


@bp.route('/<int:kullanici_id>/preset-uygula', methods=['POST'])
@login_required
@role_required('admin')
def preset_uygula(kullanici_id):
    """Hazir preset'i bir yoneticiye hizli uygulamak icin endpoint."""
    yonetici = User.query.filter_by(id=kullanici_id, rol='yonetici').first_or_404()
    preset_key = request.form.get('preset', '')
    if preset_key not in PRESETLER:
        abort(400)

    moduller = preset_moduller(preset_key)
    KullaniciModulIzin.kullanici_izinlerini_ayarla(yonetici.id, moduller)
    db.session.commit()
    flash(f'{yonetici.tam_ad} icin "{PRESETLER[preset_key]["ad"]}" preset\'i uygulandi.', 'success')
    return redirect(url_for('kullanici.yonetici.duzenle', kullanici_id=yonetici.id))
