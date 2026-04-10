from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.not_defteri import Sinav, SinavTuru, OgrenciNot
from app.models.ders_dagitimi import Ders
from app.models.muhasebe import Ogrenci, Personel
from app.models.kayit import Sinif, Sube, OgrenciKayit
from app.not_defteri.forms import SinavForm, NotGirisForm

bp = Blueprint('sinav', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    ders_id = request.args.get('ders_id', type=int)
    sube_id = request.args.get('sube_id', type=int)
    page = request.args.get('page', 1, type=int)

    query = Sinav.query.filter_by(aktif=True)

    if ders_id:
        query = query.filter(Sinav.ders_id == ders_id)
    if sube_id:
        query = query.filter(Sinav.sube_id == sube_id)

    sinavlar = query.order_by(Sinav.tarih.desc()).paginate(page=page, per_page=20)

    dersler = Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    subeler = Sube.query.join(Sube.sinif).filter(
        Sube.aktif == True
    ).order_by(Sinif.seviye, Sube.ad).all()

    return render_template('not_defteri/sinav_listesi.html',
                           sinavlar=sinavlar,
                           dersler=dersler,
                           subeler=subeler,
                           ders_id=ders_id,
                           sube_id=sube_id)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = SinavForm()

    # Seçenekleri doldur
    form.sinav_turu_id.choices = [
        (t.id, t.ad) for t in SinavTuru.query.filter_by(aktif=True).all()
    ]
    form.ders_id.choices = [
        (d.id, f'{d.kod} - {d.ad}') for d in Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    ]
    form.sube_id.choices = [
        (s.id, s.tam_ad) for s in Sube.query.join(Sube.sinif).filter(
            Sube.aktif == True
        ).order_by(Sinif.seviye, Sube.ad).all()
    ]
    form.ogretmen_id.choices = [
        (p.id, f'{p.tam_ad} ({p.sicil_no})') for p in Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    ]

    if form.validate_on_submit():
        sinav = Sinav(
            ad=form.ad.data,
            sinav_turu_id=form.sinav_turu_id.data,
            ders_id=form.ders_id.data,
            sube_id=form.sube_id.data,
            ogretmen_id=form.ogretmen_id.data,
            tarih=form.tarih.data,
            donem=form.donem.data,
            aciklama=form.aciklama.data or None,
        )
        db.session.add(sinav)
        db.session.commit()
        flash('Sınav başarıyla oluşturuldu.', 'success')
        return redirect(url_for('not_defteri.sinav.liste'))

    return render_template('not_defteri/sinav_form.html',
                           form=form, baslik='Yeni Sınav')


@bp.route('/<int:sinav_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(sinav_id):
    sinav = Sinav.query.get_or_404(sinav_id)
    form = SinavForm(obj=sinav)

    form.sinav_turu_id.choices = [
        (t.id, t.ad) for t in SinavTuru.query.filter_by(aktif=True).all()
    ]
    form.ders_id.choices = [
        (d.id, f'{d.kod} - {d.ad}') for d in Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    ]
    form.sube_id.choices = [
        (s.id, s.tam_ad) for s in Sube.query.join(Sube.sinif).filter(
            Sube.aktif == True
        ).order_by(Sinif.seviye, Sube.ad).all()
    ]
    form.ogretmen_id.choices = [
        (p.id, f'{p.tam_ad} ({p.sicil_no})') for p in Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    ]

    if form.validate_on_submit():
        sinav.ad = form.ad.data
        sinav.sinav_turu_id = form.sinav_turu_id.data
        sinav.ders_id = form.ders_id.data
        sinav.sube_id = form.sube_id.data
        sinav.ogretmen_id = form.ogretmen_id.data
        sinav.tarih = form.tarih.data
        sinav.donem = form.donem.data
        sinav.aciklama = form.aciklama.data or None

        db.session.commit()
        flash('Sınav bilgileri güncellendi.', 'success')
        return redirect(url_for('not_defteri.sinav.liste'))

    return render_template('not_defteri/sinav_form.html',
                           form=form, baslik='Sınav Düzenle')


@bp.route('/<int:sinav_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(sinav_id):
    sinav = Sinav.query.get_or_404(sinav_id)
    ad = sinav.ad
    db.session.delete(sinav)
    db.session.commit()
    flash(f'"{ad}" sınavı silindi.', 'success')
    return redirect(url_for('not_defteri.sinav.liste'))


@bp.route('/<int:sinav_id>/not-giris', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def not_giris(sinav_id):
    sinav = Sinav.query.get_or_404(sinav_id)
    form = NotGirisForm()

    # Şubedeki aktif öğrencileri getir
    kayitlar = OgrenciKayit.query.filter_by(
        sube_id=sinav.sube_id, durum='aktif'
    ).all()
    ogrenciler = [k.ogrenci for k in kayitlar]

    # Eğer kayıt yoksa, tüm öğrencileri getir (seed data için)
    if not ogrenciler:
        ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad, Ogrenci.soyad).all()

    # Mevcut notları al
    mevcut_notlar = {}
    for not_kaydi in sinav.notlar.all():
        mevcut_notlar[not_kaydi.ogrenci_id] = not_kaydi

    if request.method == 'POST' and form.validate():
        for ogrenci in ogrenciler:
            puan_str = request.form.get(f'puan_{ogrenci.id}', '').strip()
            aciklama = request.form.get(f'aciklama_{ogrenci.id}', '').strip()

            if puan_str:
                try:
                    puan = float(puan_str)
                    if puan < 0 or puan > 100:
                        continue
                except ValueError:
                    continue

                not_kaydi = mevcut_notlar.get(ogrenci.id)
                if not_kaydi:
                    not_kaydi.puan = puan
                    not_kaydi.aciklama = aciklama or None
                    not_kaydi.hesapla_harf_notu()
                else:
                    not_kaydi = OgrenciNot(
                        sinav_id=sinav.id,
                        ogrenci_id=ogrenci.id,
                        puan=puan,
                        aciklama=aciklama or None,
                    )
                    not_kaydi.hesapla_harf_notu()
                    db.session.add(not_kaydi)
            else:
                # Puan girilmemişse, mevcut notu sil
                not_kaydi = mevcut_notlar.get(ogrenci.id)
                if not_kaydi:
                    db.session.delete(not_kaydi)

        db.session.commit()
        flash('Notlar başarıyla kaydedildi.', 'success')
        return redirect(url_for('not_defteri.sinav.sonuclar', sinav_id=sinav.id))

    return render_template('not_defteri/not_giris.html',
                           sinav=sinav,
                           form=form,
                           ogrenciler=ogrenciler,
                           mevcut_notlar=mevcut_notlar)


@bp.route('/<int:sinav_id>/sonuclar')
@login_required
@role_required('admin', 'ogretmen')
def sonuclar(sinav_id):
    sinav = Sinav.query.get_or_404(sinav_id)
    notlar = sinav.notlar.filter(OgrenciNot.puan.isnot(None)).all()

    # İstatistikler
    if notlar:
        puanlar = [n.puan for n in notlar]
        ortalama = round(sum(puanlar) / len(puanlar), 2)
        en_yuksek = max(puanlar)
        en_dusuk = min(puanlar)
        # Standart sapma
        varyans = sum((p - ortalama) ** 2 for p in puanlar) / len(puanlar)
        std_sapma = round(varyans ** 0.5, 2)

        # Not dağılımı
        dagilim = {'AA': 0, 'BA': 0, 'BB': 0, 'CB': 0, 'CC': 0,
                   'DC': 0, 'DD': 0, 'FD': 0, 'FF': 0}
        for n in notlar:
            if n.harf_notu and n.harf_notu in dagilim:
                dagilim[n.harf_notu] += 1
    else:
        ortalama = en_yuksek = en_dusuk = std_sapma = 0
        dagilim = {}

    return render_template('not_defteri/sinav_sonuclar.html',
                           sinav=sinav,
                           notlar=notlar,
                           ortalama=ortalama,
                           en_yuksek=en_yuksek,
                           en_dusuk=en_dusuk,
                           std_sapma=std_sapma,
                           dagilim=dagilim)
