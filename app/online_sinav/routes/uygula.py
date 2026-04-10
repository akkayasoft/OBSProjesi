from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from datetime import datetime
from app.extensions import db
from app.models.online_sinav import (OnlineSinav, SinavSoru, SinavKatilim,
                                     OgrenciCevap, SoruSecenegi)
from app.models.muhasebe import Ogrenci

bp = Blueprint('uygula', __name__)


@bp.route('/<int:sinav_id>')
@login_required
@role_required('admin', 'ogretmen', 'ogrenci')
def baslat(sinav_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)

    # Ogrenci sec (ilk aktif ogrenci - simulasyon icin)
    ogrenci_id = request.args.get('ogrenci_id', type=int)
    if not ogrenci_id:
        ogrenci = Ogrenci.query.filter_by(aktif=True).first()
        if not ogrenci:
            flash('Aktif öğrenci bulunamadı.', 'danger')
            return redirect(url_for('online_sinav.sinav.detay', sinav_id=sinav.id))
        ogrenci_id = ogrenci.id
    else:
        ogrenci = Ogrenci.query.get_or_404(ogrenci_id)

    # Katilim olustur veya mevcut olani al
    katilim = SinavKatilim.query.filter_by(
        sinav_id=sinav.id, ogrenci_id=ogrenci_id
    ).first()

    if not katilim:
        katilim = SinavKatilim(
            sinav_id=sinav.id,
            ogrenci_id=ogrenci_id,
            baslama_zamani=datetime.utcnow(),
            durum='devam_ediyor',
        )
        db.session.add(katilim)
        db.session.commit()
    elif katilim.durum in ['tamamlandi', 'suresi_doldu']:
        # Zaten tamamlanmis, sonuc sayfasina yonlendir
        flash('Bu sınavı zaten tamamladınız.', 'info')
        return redirect(url_for('online_sinav.uygula.sonuc', sinav_id=sinav.id, ogrenci_id=ogrenci_id))
    elif katilim.durum == 'baslamadi':
        katilim.baslama_zamani = datetime.utcnow()
        katilim.durum = 'devam_ediyor'
        db.session.commit()

    sorular = sinav.sorular.order_by(SinavSoru.sira).all()

    # Mevcut cevaplari getir
    mevcut_cevaplar = {}
    for cevap in katilim.cevaplar.all():
        mevcut_cevaplar[cevap.soru_id] = cevap

    # Ogrenci listesi (simulasyon icin)
    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()

    return render_template('online_sinav/sinav_uygula.html',
                           sinav=sinav,
                           katilim=katilim,
                           sorular=sorular,
                           ogrenci=ogrenci,
                           ogrenciler=ogrenciler,
                           mevcut_cevaplar=mevcut_cevaplar)


@bp.route('/<int:sinav_id>/cevapla', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen', 'ogrenci')
def cevapla(sinav_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)
    ogrenci_id = request.form.get('ogrenci_id', type=int)

    if not ogrenci_id:
        flash('Öğrenci bilgisi bulunamadı.', 'danger')
        return redirect(url_for('online_sinav.sinav.detay', sinav_id=sinav.id))

    katilim = SinavKatilim.query.filter_by(
        sinav_id=sinav.id, ogrenci_id=ogrenci_id
    ).first()

    if not katilim:
        flash('Sınav katılımı bulunamadı.', 'danger')
        return redirect(url_for('online_sinav.sinav.detay', sinav_id=sinav.id))

    if katilim.durum in ['tamamlandi', 'suresi_doldu']:
        flash('Bu sınav zaten tamamlanmış.', 'warning')
        return redirect(url_for('online_sinav.uygula.sonuc', sinav_id=sinav.id, ogrenci_id=ogrenci_id))

    # Mevcut cevaplari temizle
    OgrenciCevap.query.filter_by(katilim_id=katilim.id).delete()

    toplam_puan = 0
    sorular = sinav.sorular.all()

    for soru in sorular:
        cevap = OgrenciCevap(
            katilim_id=katilim.id,
            soru_id=soru.id,
        )

        if soru.soru_turu == 'coktan_secmeli':
            secilen_id = request.form.get(f'soru_{soru.id}', type=int)
            cevap.secilen_secenek_id = secilen_id
            if secilen_id:
                secenek = SoruSecenegi.query.get(secilen_id)
                if secenek and secenek.dogru_mu:
                    cevap.dogru_mu = True
                    cevap.puan = soru.puan
                    toplam_puan += soru.puan
                else:
                    cevap.dogru_mu = False
                    cevap.puan = 0

        elif soru.soru_turu == 'dogru_yanlis':
            cevap_val = request.form.get(f'soru_{soru.id}')
            if cevap_val is not None:
                cevap.dogru_yanlis_cevap = (cevap_val == 'true')
                dogru_secenek = soru.secenekler.filter_by(dogru_mu=True).first()
                if dogru_secenek:
                    beklenen = (dogru_secenek.secenek_metni == 'Doğru')
                    if cevap.dogru_yanlis_cevap == beklenen:
                        cevap.dogru_mu = True
                        cevap.puan = soru.puan
                        toplam_puan += soru.puan
                    else:
                        cevap.dogru_mu = False
                        cevap.puan = 0

        elif soru.soru_turu == 'klasik':
            cevap.cevap_metni = request.form.get(f'soru_{soru.id}', '')
            # Klasik sorular manuel puanlanir
            cevap.puan = None
            cevap.dogru_mu = None

        elif soru.soru_turu == 'bosluk_doldurma':
            cevap.cevap_metni = request.form.get(f'soru_{soru.id}', '').strip()
            dogru_secenek = soru.secenekler.filter_by(dogru_mu=True).first()
            if dogru_secenek and cevap.cevap_metni:
                if cevap.cevap_metni.lower() == dogru_secenek.secenek_metni.lower():
                    cevap.dogru_mu = True
                    cevap.puan = soru.puan
                    toplam_puan += soru.puan
                else:
                    cevap.dogru_mu = False
                    cevap.puan = 0

        db.session.add(cevap)

    # Klasik soru var mi kontrol et
    klasik_var = any(s.soru_turu == 'klasik' for s in sorular)

    katilim.bitirme_zamani = datetime.utcnow()
    katilim.durum = 'tamamlandi'
    if not klasik_var:
        katilim.toplam_puan = toplam_puan
    else:
        # Sadece otomatik puanlanan sorularin toplami
        katilim.toplam_puan = toplam_puan

    db.session.commit()
    flash('Sınav başarıyla tamamlandı!', 'success')
    return redirect(url_for('online_sinav.uygula.sonuc', sinav_id=sinav.id, ogrenci_id=ogrenci_id))


@bp.route('/<int:sinav_id>/sonuc')
@login_required
@role_required('admin', 'ogretmen', 'ogrenci')
def sonuc(sinav_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)
    ogrenci_id = request.args.get('ogrenci_id', type=int)

    if not ogrenci_id:
        flash('Öğrenci bilgisi gerekli.', 'danger')
        return redirect(url_for('online_sinav.sinav.detay', sinav_id=sinav.id))

    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    katilim = SinavKatilim.query.filter_by(
        sinav_id=sinav.id, ogrenci_id=ogrenci_id
    ).first_or_404()

    sorular = sinav.sorular.order_by(SinavSoru.sira).all()
    cevaplar = {}
    for cevap in katilim.cevaplar.all():
        cevaplar[cevap.soru_id] = cevap

    return render_template('online_sinav/sinav_sonuc.html',
                           sinav=sinav,
                           ogrenci=ogrenci,
                           katilim=katilim,
                           sorular=sorular,
                           cevaplar=cevaplar)
