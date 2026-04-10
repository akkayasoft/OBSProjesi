from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.iletisim import TopluMesaj, TopluMesajAlici, IletisimDefteri
from app.models.muhasebe import Personel, Ogrenci
from app.iletisim.forms import TopluMesajForm
from datetime import datetime
import random

bp = Blueprint('toplu', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def liste():
    page = request.args.get('page', 1, type=int)

    mesajlar = TopluMesaj.query.order_by(
        TopluMesaj.created_at.desc()
    ).paginate(page=page, per_page=20)

    return render_template('iletisim/toplu_listesi.html', mesajlar=mesajlar)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def yeni():
    form = TopluMesajForm()

    # Sınıf listesini doldur
    siniflar = db.session.query(Ogrenci.sinif).filter(
        Ogrenci.sinif.isnot(None),
        Ogrenci.aktif == True
    ).distinct().order_by(Ogrenci.sinif).all()
    sinif_choices = [('', 'Sınıf seçiniz')] + [(s[0], s[0]) for s in siniflar if s[0]]
    form.hedef_sinif.choices = sinif_choices

    if form.validate_on_submit():
        toplu_mesaj = TopluMesaj(
            gonderen_id=current_user.id,
            baslik=form.baslik.data,
            icerik=form.icerik.data,
            hedef_grup=form.hedef_grup.data,
            hedef_sinif=form.hedef_sinif.data if form.hedef_grup.data == 'sinif' else None,
            gonderim_turu=form.gonderim_turu.data,
            durum='beklemede',
        )
        db.session.add(toplu_mesaj)
        db.session.flush()

        # Alıcıları belirle
        alicilar = _hedef_alicilari_getir(form.hedef_grup.data, form.hedef_sinif.data)
        toplu_mesaj.toplam_alici = len(alicilar)

        for alici_adi, alici_iletisim in alicilar:
            db.session.add(TopluMesajAlici(
                toplu_mesaj_id=toplu_mesaj.id,
                alici_adi=alici_adi,
                alici_iletisim=alici_iletisim,
                durum='beklemede',
            ))

        db.session.commit()
        flash('Toplu mesaj oluşturuldu. Göndermek için detay sayfasından gönder butonuna tıklayın.', 'success')
        return redirect(url_for('iletisim.toplu.detay', mesaj_id=toplu_mesaj.id))

    return render_template('iletisim/toplu_form.html', form=form, baslik='Yeni Toplu Mesaj')


@bp.route('/<int:mesaj_id>')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def detay(mesaj_id):
    mesaj = TopluMesaj.query.get_or_404(mesaj_id)
    alicilar = mesaj.alicilar.order_by(TopluMesajAlici.alici_adi).all()
    return render_template('iletisim/toplu_detay.html', mesaj=mesaj, alicilar=alicilar)


@bp.route('/<int:mesaj_id>/gonder', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def gonder(mesaj_id):
    mesaj = TopluMesaj.query.get_or_404(mesaj_id)

    if mesaj.durum == 'gonderildi':
        flash('Bu mesaj zaten gönderilmiş.', 'warning')
        return redirect(url_for('iletisim.toplu.detay', mesaj_id=mesaj.id))

    # Simüle et: alıcıları gönderildi olarak işaretle
    basarili = 0
    for alici in mesaj.alicilar.all():
        # %90 başarı oranı simülasyonu
        if random.random() < 0.9:
            alici.durum = 'gonderildi'
            basarili += 1
        else:
            alici.durum = 'basarisiz'
            alici.hata_mesaji = 'Geçici bağlantı hatası (simülasyon)'

    mesaj.durum = 'gonderildi'
    mesaj.basarili_gonderim = basarili
    mesaj.gonderim_tarihi = datetime.utcnow()
    db.session.commit()

    flash(f'Mesaj gönderildi. {basarili}/{mesaj.toplam_alici} alıcıya başarıyla ulaştı.', 'success')
    return redirect(url_for('iletisim.toplu.detay', mesaj_id=mesaj.id))


def _hedef_alicilari_getir(hedef_grup, hedef_sinif=None):
    """Hedef gruba göre alıcı listesi döndürür: [(ad, iletisim), ...]"""
    alicilar = []

    if hedef_grup == 'ogretmenler' or hedef_grup == 'tumu':
        personeller = Personel.query.filter_by(aktif=True).all()
        for p in personeller:
            iletisim = p.telefon or p.email or 'Bilgi yok'
            alicilar.append((p.tam_ad, iletisim))

    if hedef_grup == 'veliler' or hedef_grup == 'tumu':
        rehber = IletisimDefteri.query.filter_by(kategori='veli', aktif=True).all()
        for r in rehber:
            alicilar.append((r.tam_ad, r.telefon))
        # Ayrıca öğrenci veli bilgilerinden
        ogrenciler = Ogrenci.query.filter(
            Ogrenci.aktif == True,
            Ogrenci.veli_telefon.isnot(None)
        ).all()
        mevcut_telefonlar = {a[1] for a in alicilar}
        for o in ogrenciler:
            if o.veli_telefon and o.veli_telefon not in mevcut_telefonlar:
                veli_ad = o.veli_ad or f"{o.ad} {o.soyad} Velisi"
                alicilar.append((veli_ad, o.veli_telefon))
                mevcut_telefonlar.add(o.veli_telefon)

    if hedef_grup == 'personel' or hedef_grup == 'tumu':
        personeller = Personel.query.filter_by(aktif=True).all()
        mevcut = {a[1] for a in alicilar}
        for p in personeller:
            iletisim = p.telefon or p.email or 'Bilgi yok'
            if iletisim not in mevcut:
                alicilar.append((p.tam_ad, iletisim))
                mevcut.add(iletisim)

    if hedef_grup == 'sinif' and hedef_sinif:
        ogrenciler = Ogrenci.query.filter_by(sinif=hedef_sinif, aktif=True).all()
        for o in ogrenciler:
            iletisim = o.veli_telefon or o.telefon or 'Bilgi yok'
            veli_ad = o.veli_ad or f"{o.ad} {o.soyad} Velisi"
            alicilar.append((veli_ad, iletisim))

    return alicilar
