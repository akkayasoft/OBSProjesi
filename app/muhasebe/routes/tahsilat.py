from datetime import date, datetime, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from sqlalchemy import func, or_
from app.models.muhasebe import (
    Odeme, Taksit, OdemePlani, Ogrenci, BankaHesabi, BankaHareketi
)
from app.muhasebe.utils import banka_hareketi_olustur

bp = Blueprint('tahsilat', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'muhasebeci')
def liste():
    """Tum tahsilatlar - filtreleme ve kasa ozeti ile."""
    from app.muhasebe.utils import geciken_taksitleri_guncelle
    geciken_taksitleri_guncelle()

    page = request.args.get('page', 1, type=int)
    arama = request.args.get('q', '').strip()
    baslangic = request.args.get('baslangic', '')
    bitis = request.args.get('bitis', '')
    odeme_turu = request.args.get('odeme_turu', '')
    banka_id = request.args.get('banka_id', type=int)
    durum = request.args.get('durum', 'aktif')  # aktif, iptal, hepsi

    bugun = date.today()
    # Varsayilan: bu ayin basindan bugune
    if not baslangic:
        baslangic_tarih = bugun.replace(day=1)
        baslangic = baslangic_tarih.isoformat()
    else:
        try:
            baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d').date()
        except ValueError:
            baslangic_tarih = bugun.replace(day=1)

    if not bitis:
        bitis_tarih = bugun
        bitis = bitis_tarih.isoformat()
    else:
        try:
            bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d').date()
        except ValueError:
            bitis_tarih = bugun

    query = Odeme.query.filter(
        Odeme.tarih >= datetime.combine(baslangic_tarih, datetime.min.time()),
        Odeme.tarih <= datetime.combine(bitis_tarih, datetime.max.time())
    )

    if durum == 'aktif':
        query = query.filter(Odeme.iptal_edildi.isnot(True))
    elif durum == 'iptal':
        query = query.filter(Odeme.iptal_edildi.is_(True))

    if odeme_turu:
        query = query.filter(Odeme.odeme_turu == odeme_turu)

    if banka_id:
        query = query.filter(Odeme.banka_hesap_id == banka_id)

    if arama:
        query = query.join(Taksit).join(OdemePlani).join(Ogrenci).filter(
            or_(
                Ogrenci.ad.ilike(f'%{arama}%'),
                Ogrenci.soyad.ilike(f'%{arama}%'),
                Ogrenci.ogrenci_no.ilike(f'%{arama}%'),
                Odeme.makbuz_no.ilike(f'%{arama}%')
            )
        )

    odemeler = query.order_by(Odeme.tarih.desc()).paginate(
        page=page, per_page=30, error_out=False
    )

    # Ozet hesaplamalar (tum donem icin, pagination disi)
    ozet_query = Odeme.query.filter(
        Odeme.tarih >= datetime.combine(baslangic_tarih, datetime.min.time()),
        Odeme.tarih <= datetime.combine(bitis_tarih, datetime.max.time()),
        Odeme.iptal_edildi.isnot(True)
    )

    toplam_tahsilat = float(
        ozet_query.with_entities(func.coalesce(func.sum(Odeme.tutar), 0)).scalar() or 0
    )

    nakit_toplam = float(
        ozet_query.filter(Odeme.odeme_turu == 'nakit').with_entities(
            func.coalesce(func.sum(Odeme.tutar), 0)
        ).scalar() or 0
    )
    banka_toplam = toplam_tahsilat - nakit_toplam

    # Odeme turune gore dagilim
    tur_dagilim = db.session.query(
        Odeme.odeme_turu,
        func.coalesce(func.sum(Odeme.tutar), 0)
    ).filter(
        Odeme.tarih >= datetime.combine(baslangic_tarih, datetime.min.time()),
        Odeme.tarih <= datetime.combine(bitis_tarih, datetime.max.time()),
        Odeme.iptal_edildi.isnot(True)
    ).group_by(Odeme.odeme_turu).all()

    # Gunluk trend (son 30 gun)
    gunluk_trend = []
    trend_baslangic = bitis_tarih - timedelta(days=29)
    for i in range(30):
        gun = trend_baslangic + timedelta(days=i)
        gun_tutar = db.session.query(
            func.coalesce(func.sum(Odeme.tutar), 0)
        ).filter(
            func.date(Odeme.tarih) == gun,
            Odeme.iptal_edildi.isnot(True)
        ).scalar() or 0
        gunluk_trend.append({
            'tarih': gun.strftime('%d.%m'),
            'tutar': float(gun_tutar)
        })

    banka_hesaplari = BankaHesabi.query.filter_by(aktif=True).all()

    return render_template('muhasebe/tahsilat/liste.html',
                           odemeler=odemeler,
                           arama=arama,
                           baslangic=baslangic,
                           bitis=bitis,
                           odeme_turu=odeme_turu,
                           banka_id=banka_id,
                           durum=durum,
                           toplam_tahsilat=toplam_tahsilat,
                           nakit_toplam=nakit_toplam,
                           banka_toplam=banka_toplam,
                           tur_dagilim=tur_dagilim,
                           gunluk_trend=gunluk_trend,
                           banka_hesaplari=banka_hesaplari)


@bp.route('/odeme/<int:odeme_id>/iptal', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci')
def odeme_iptal(odeme_id):
    """Odemeyi iptal et - taksit odenen tutarini geri al, banka bakiyesini guncelle."""
    odeme = Odeme.query.get_or_404(odeme_id)

    if odeme.iptal_edildi:
        flash('Bu ödeme zaten iptal edilmiş.', 'warning')
        return redirect(url_for('muhasebe.tahsilat.liste'))

    if request.method == 'POST':
        neden = request.form.get('neden', '').strip()
        if not neden:
            flash('İptal nedeni belirtmelisiniz.', 'danger')
            return render_template('muhasebe/tahsilat/odeme_iptal.html', odeme=odeme)

        taksit = odeme.taksit
        tutar = Decimal(str(odeme.tutar))

        # Taksit odenen tutarini geri al
        taksit.odenen_tutar = Decimal(str(taksit.odenen_tutar)) - tutar
        if float(taksit.odenen_tutar) < 0:
            taksit.odenen_tutar = 0
        taksit.durum_guncelle()

        # Banka bakiyesi ve hareket
        if odeme.banka_hesap_id:
            banka_hareketi_olustur(
                odeme.banka_hesap_id, 'cikis', odeme.tutar,
                aciklama=f'Ödeme iptali (İade) - Makbuz: {odeme.makbuz_no}'
            )

        # Iptal bilgilerini kaydet
        odeme.iptal_edildi = True
        odeme.iptal_tarihi = datetime.utcnow()
        odeme.iptal_nedeni = neden[:200]
        odeme.iptal_eden_id = current_user.id

        db.session.commit()
        flash(f'{odeme.makbuz_no} numaralı ödeme iptal edildi ve {float(tutar):,.2f} ₺ iade işlemi yapıldı.',
              'success')
        return redirect(url_for('muhasebe.tahsilat.liste'))

    return render_template('muhasebe/tahsilat/odeme_iptal.html', odeme=odeme)


@bp.route('/taksit/<int:taksit_id>/ertele', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci')
def taksit_ertele(taksit_id):
    """Taksit vade tarihini ileri al."""
    taksit = Taksit.query.get_or_404(taksit_id)

    if taksit.durum == 'odendi':
        flash('Ödenmiş taksit ertelenemez.', 'warning')
        return redirect(url_for('muhasebe.ogrenci_odeme.detay',
                                ogrenci_id=taksit.odeme_plani.ogrenci_id))

    if request.method == 'POST':
        yeni_vade_str = request.form.get('yeni_vade', '')
        not_metni = request.form.get('not_metni', '').strip()

        try:
            yeni_vade = datetime.strptime(yeni_vade_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Geçerli bir tarih giriniz.', 'danger')
            return render_template('muhasebe/tahsilat/taksit_ertele.html', taksit=taksit)

        if yeni_vade <= taksit.vade_tarihi:
            flash('Yeni vade tarihi mevcut vadeden sonraki bir tarih olmalıdır.', 'danger')
            return render_template('muhasebe/tahsilat/taksit_ertele.html', taksit=taksit)

        # Orjinal vade tarihini ilk ertelemede kaydet
        if not taksit.orjinal_vade_tarihi:
            taksit.orjinal_vade_tarihi = taksit.vade_tarihi

        taksit.vade_tarihi = yeni_vade
        taksit.erteleme_notu = not_metni[:200] if not_metni else None
        taksit.durum_guncelle()

        db.session.commit()
        flash(f'{taksit.taksit_no}. taksit vadesi {yeni_vade.strftime("%d.%m.%Y")} tarihine ertelendi.',
              'success')
        return redirect(url_for('muhasebe.ogrenci_odeme.detay',
                                ogrenci_id=taksit.odeme_plani.ogrenci_id))

    return render_template('muhasebe/tahsilat/taksit_ertele.html', taksit=taksit)


@bp.route('/plan/<int:plan_id>/yeniden-yapilandir', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci')
def plan_yeniden_yapilandir(plan_id):
    """Mevcut planin kalan borcunu kapat, yeni plan olustur."""
    plan = OdemePlani.query.get_or_404(plan_id)
    ogrenci = plan.ogrenci

    if plan.durum != 'aktif':
        flash('Bu plan zaten kapalı veya iptal edilmiş.', 'warning')
        return redirect(url_for('muhasebe.ogrenci_odeme.detay', ogrenci_id=ogrenci.id))

    kalan_borc = plan.kalan_borc
    if kalan_borc <= 0:
        flash('Bu planın kalan borcu yok, yeniden yapılandırma gerekmiyor.', 'info')
        return redirect(url_for('muhasebe.ogrenci_odeme.detay', ogrenci_id=ogrenci.id))

    if request.method == 'POST':
        try:
            yeni_taksit_sayisi = int(request.form.get('taksit_sayisi', 0))
            yeni_toplam = Decimal(request.form.get('yeni_toplam', str(kalan_borc)))
            ilk_vade_str = request.form.get('ilk_vade', '')
            donem = request.form.get('donem', plan.donem).strip()
            neden = request.form.get('neden', '').strip()

            if yeni_taksit_sayisi < 1 or yeni_taksit_sayisi > 24:
                flash('Taksit sayısı 1 ile 24 arasında olmalıdır.', 'danger')
                return render_template('muhasebe/tahsilat/yeniden_yapilandir.html',
                                       plan=plan, ogrenci=ogrenci, kalan_borc=kalan_borc)

            if yeni_toplam <= 0:
                flash('Yeni toplam tutar pozitif olmalıdır.', 'danger')
                return render_template('muhasebe/tahsilat/yeniden_yapilandir.html',
                                       plan=plan, ogrenci=ogrenci, kalan_borc=kalan_borc)

            ilk_vade = datetime.strptime(ilk_vade_str, '%Y-%m-%d').date() if ilk_vade_str \
                else (date.today() + timedelta(days=30))
        except (ValueError, TypeError):
            flash('Lütfen tüm alanları doğru formatta doldurun.', 'danger')
            return render_template('muhasebe/tahsilat/yeniden_yapilandir.html',
                                   plan=plan, ogrenci=ogrenci, kalan_borc=kalan_borc)

        # Eski plani kapat (oduleri silmeden, sadece durumu degistir)
        plan.durum = 'kapali'
        plan.kapanma_tarihi = datetime.utcnow()
        plan.kapanma_nedeni = f'Yeniden yapılandırıldı: {neden[:150]}' if neden else 'Yeniden yapılandırıldı'

        # Eski plandaki odenmemis taksitleri iptal et
        for tks in plan.taksitler:
            if tks.durum != 'odendi':
                # Kalan tutari sifirla ki toplam borca eklenmesin
                tks.tutar = Decimal(str(tks.odenen_tutar))
                if float(tks.odenen_tutar) > 0:
                    tks.durum = 'odendi'
                else:
                    tks.durum = 'iptal'

        # Yeni plan olustur
        yeni_plan = OdemePlani(
            ogrenci_id=ogrenci.id,
            donem=donem,
            toplam_tutar=yeni_toplam,
            indirim_tutar=0,
            taksit_sayisi=yeni_taksit_sayisi,
            aciklama=f'{plan.donem} planının yeniden yapılandırılması. Sebep: {neden}' if neden
                     else f'{plan.donem} planından yeniden yapılandırıldı',
            onceki_plan_id=plan.id,
            durum='aktif'
        )
        db.session.add(yeni_plan)
        db.session.flush()

        # Yeni taksitleri olustur
        taksit_tutar = yeni_toplam / yeni_taksit_sayisi
        kalan_yuvarlama = yeni_toplam - (taksit_tutar * yeni_taksit_sayisi)

        for i in range(yeni_taksit_sayisi):
            tutar = taksit_tutar
            if i == yeni_taksit_sayisi - 1:
                tutar += kalan_yuvarlama
            vade = ilk_vade + timedelta(days=30 * i)
            yeni_taksit = Taksit(
                odeme_plani_id=yeni_plan.id,
                taksit_no=i + 1,
                tutar=tutar,
                vade_tarihi=vade,
                odenen_tutar=0,
                durum='beklemede'
            )
            db.session.add(yeni_taksit)

        db.session.commit()
        flash(f'{plan.donem} planı yeniden yapılandırıldı. Yeni plan {yeni_taksit_sayisi} taksit olarak oluşturuldu.',
              'success')
        return redirect(url_for('muhasebe.ogrenci_odeme.detay', ogrenci_id=ogrenci.id))

    return render_template('muhasebe/tahsilat/yeniden_yapilandir.html',
                           plan=plan, ogrenci=ogrenci, kalan_borc=kalan_borc)


@bp.route('/hatirlatma', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci')
def toplu_hatirlatma():
    """Geciken/yaklaşan ödemeler icin toplu bildirim gonder."""
    from app.muhasebe.utils import geciken_taksitleri_guncelle
    geciken_taksitleri_guncelle()

    bugun = date.today()
    secim = request.args.get('secim', 'geciken')  # geciken, yaklasan

    if secim == 'yaklasan':
        yaklasan_tarih = bugun + timedelta(days=7)
        taksitler = Taksit.query.filter(
            Taksit.durum.in_(['beklemede', 'kismi_odendi']),
            Taksit.vade_tarihi >= bugun,
            Taksit.vade_tarihi <= yaklasan_tarih
        ).join(OdemePlani).join(Ogrenci).filter(Ogrenci.aktif.is_(True)).all()
    else:
        taksitler = Taksit.query.filter(
            Taksit.durum.in_(['gecikti', 'kismi_odendi']),
            Taksit.vade_tarihi < bugun
        ).join(OdemePlani).join(Ogrenci).filter(Ogrenci.aktif.is_(True)).all()

    if request.method == 'POST':
        try:
            from app.models.bildirim import Bildirim
        except ImportError:
            flash('Bildirim modeli bulunamadı.', 'danger')
            return redirect(url_for('muhasebe.tahsilat.toplu_hatirlatma'))

        mesaj = request.form.get('mesaj', '').strip()
        if not mesaj:
            flash('Mesaj içeriği boş olamaz.', 'danger')
            return render_template('muhasebe/tahsilat/hatirlatma.html',
                                   taksitler=taksitler, secim=secim, bugun=bugun)

        gonderilen = 0
        for tks in taksitler:
            ogrenci = tks.odeme_plani.ogrenci
            if ogrenci.user_id:
                icerik = mesaj.replace('{ad}', ogrenci.tam_ad) \
                              .replace('{tutar}', f'{tks.kalan:,.2f} ₺') \
                              .replace('{vade}', tks.vade_tarihi.strftime('%d.%m.%Y'))
                try:
                    b = Bildirim(
                        kullanici_id=ogrenci.user_id,
                        baslik='Ödeme Hatırlatması',
                        mesaj=icerik,
                        tur='uyari',
                        kategori='odeme'
                    )
                    db.session.add(b)
                    gonderilen += 1
                except Exception:
                    continue

        db.session.commit()
        flash(f'{gonderilen} öğrenciye hatırlatma bildirimi gönderildi.', 'success')
        return redirect(url_for('muhasebe.tahsilat.liste'))

    return render_template('muhasebe/tahsilat/hatirlatma.html',
                           taksitler=taksitler, secim=secim, bugun=bugun)
