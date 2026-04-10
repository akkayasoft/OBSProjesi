from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.karne import Karne, KarneDersNotu
from app.models.muhasebe import Ogrenci
from app.models.kayit import Sinif, Sube, OgrenciKayit
from app.karne.forms import KarneForm, KarneDersNotuForm, TopluKarneForm

bp = Blueprint('karne_routes', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    sinif_id = request.args.get('sinif_id', 0, type=int)
    donem = request.args.get('donem', '')
    ogretim_yili = request.args.get('ogretim_yili', '')
    durum = request.args.get('durum', '')
    arama = request.args.get('arama', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Karne.query

    if sinif_id:
        query = query.filter(Karne.sinif_id == sinif_id)
    if donem:
        query = query.filter(Karne.donem == donem)
    if ogretim_yili:
        query = query.filter(Karne.ogretim_yili == ogretim_yili)
    if durum:
        query = query.filter(Karne.durum == durum)
    if arama:
        query = query.join(Ogrenci).filter(
            db.or_(
                Ogrenci.ad.ilike(f'%{arama}%'),
                Ogrenci.soyad.ilike(f'%{arama}%'),
                Ogrenci.ogrenci_no.ilike(f'%{arama}%')
            )
        )

    karneler = query.order_by(Karne.created_at.desc()).paginate(page=page, per_page=20)
    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.seviye).all()

    return render_template('karne/karne_listesi.html',
                           karneler=karneler,
                           siniflar=siniflar,
                           sinif_id=sinif_id,
                           donem=donem,
                           ogretim_yili=ogretim_yili,
                           durum=durum,
                           arama=arama)


@bp.route('/olustur', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def olustur():
    form = TopluKarneForm()
    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.seviye).all()
    form.sinif_id.choices = [(s.id, s.ad) for s in siniflar]

    if form.validate_on_submit():
        sinif_id = form.sinif_id.data
        donem_val = form.donem.data
        ogretim_yili_val = form.ogretim_yili.data

        # Sinifa kayitli ogrencileri bul
        kayitlar = OgrenciKayit.query.filter_by(
            sinif_id=sinif_id, aktif=True
        ).all()

        if not kayitlar:
            flash('Secilen sinifta kayitli ogrenci bulunamadi.', 'warning')
            return render_template('karne/karne_olustur.html', form=form)

        olusturulan = 0
        atlanan = 0
        for kayit in kayitlar:
            # Ayni donem ve ogretim yilinda karne var mi kontrol et
            mevcut = Karne.query.filter_by(
                ogrenci_id=kayit.ogrenci_id,
                donem=donem_val,
                ogretim_yili=ogretim_yili_val
            ).first()
            if mevcut:
                atlanan += 1
                continue

            karne = Karne(
                ogrenci_id=kayit.ogrenci_id,
                donem=donem_val,
                ogretim_yili=ogretim_yili_val,
                sinif_id=sinif_id,
                durum='taslak'
            )
            db.session.add(karne)
            olusturulan += 1

        db.session.commit()
        flash(f'{olusturulan} karne olusturuldu. {atlanan} ogrenci icin karne zaten mevcut.', 'success')
        return redirect(url_for('karne.karne_routes.liste', sinif_id=sinif_id))

    return render_template('karne/karne_olustur.html', form=form)


@bp.route('/<int:karne_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(karne_id):
    karne = Karne.query.get_or_404(karne_id)
    ders_notlari = karne.ders_notlari.order_by(KarneDersNotu.ders_adi).all()
    return render_template('karne/karne_detay.html',
                           karne=karne,
                           ders_notlari=ders_notlari)


@bp.route('/<int:karne_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(karne_id):
    karne = Karne.query.get_or_404(karne_id)
    form = KarneForm(obj=karne)

    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.seviye).all()
    form.sinif_id.choices = [(s.id, s.ad) for s in siniflar]
    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}')
                                for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()]

    if form.validate_on_submit():
        karne.ogrenci_id = form.ogrenci_id.data
        karne.donem = form.donem.data
        karne.ogretim_yili = form.ogretim_yili.data
        karne.sinif_id = form.sinif_id.data
        karne.davranis_notu = form.davranis_notu.data
        karne.devamsizlik_ozetsiz = int(form.devamsizlik_ozetsiz.data or 0)
        karne.devamsizlik_ozetli = int(form.devamsizlik_ozetli.data or 0)
        karne.sinif_ogretmeni_notu = form.sinif_ogretmeni_notu.data
        karne.mudur_notu = form.mudur_notu.data
        karne.durum = form.durum.data

        # Genel ortalama hesapla
        karne.hesapla_genel_ortalama()

        db.session.commit()
        flash('Karne basariyla guncellendi.', 'success')
        return redirect(url_for('karne.karne_routes.detay', karne_id=karne.id))

    return render_template('karne/karne_duzenle.html',
                           form=form, karne=karne, baslik='Karne Duzenle')


@bp.route('/<int:karne_id>/ders-notu/ekle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def ders_notu_ekle(karne_id):
    karne = Karne.query.get_or_404(karne_id)
    form = KarneDersNotuForm()

    if form.validate_on_submit():
        ders_notu = KarneDersNotu(
            karne_id=karne.id,
            ders_adi=form.ders_adi.data,
            ders_kodu=form.ders_kodu.data,
            sinav1=form.sinav1.data,
            sinav2=form.sinav2.data,
            sinav3=form.sinav3.data,
            ortalama=form.ortalama.data,
            performans=form.performans.data,
            proje=form.proje.data,
            yilsonu=form.yilsonu.data,
        )
        ders_notu.hesapla_harf_notu()
        db.session.add(ders_notu)

        # Genel ortalama guncelle
        karne.hesapla_genel_ortalama()
        db.session.commit()

        flash(f'{ders_notu.ders_adi} ders notu eklendi.', 'success')
        return redirect(url_for('karne.karne_routes.detay', karne_id=karne.id))

    return render_template('karne/ders_notu_form.html',
                           form=form, karne=karne, baslik='Ders Notu Ekle')


@bp.route('/<int:karne_id>/ders-notu/<int:ders_notu_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def ders_notu_duzenle(karne_id, ders_notu_id):
    karne = Karne.query.get_or_404(karne_id)
    ders_notu = KarneDersNotu.query.get_or_404(ders_notu_id)

    if ders_notu.karne_id != karne.id:
        flash('Ders notu bu karneye ait degil.', 'danger')
        return redirect(url_for('karne.karne_routes.detay', karne_id=karne.id))

    form = KarneDersNotuForm(obj=ders_notu)

    if form.validate_on_submit():
        ders_notu.ders_adi = form.ders_adi.data
        ders_notu.ders_kodu = form.ders_kodu.data
        ders_notu.sinav1 = form.sinav1.data
        ders_notu.sinav2 = form.sinav2.data
        ders_notu.sinav3 = form.sinav3.data
        ders_notu.ortalama = form.ortalama.data
        ders_notu.performans = form.performans.data
        ders_notu.proje = form.proje.data
        ders_notu.yilsonu = form.yilsonu.data
        ders_notu.hesapla_harf_notu()

        karne.hesapla_genel_ortalama()
        db.session.commit()

        flash(f'{ders_notu.ders_adi} ders notu guncellendi.', 'success')
        return redirect(url_for('karne.karne_routes.detay', karne_id=karne.id))

    return render_template('karne/ders_notu_form.html',
                           form=form, karne=karne, baslik='Ders Notu Duzenle')


@bp.route('/<int:karne_id>/ders-notu/<int:ders_notu_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def ders_notu_sil(karne_id, ders_notu_id):
    karne = Karne.query.get_or_404(karne_id)
    ders_notu = KarneDersNotu.query.get_or_404(ders_notu_id)

    if ders_notu.karne_id != karne.id:
        flash('Ders notu bu karneye ait degil.', 'danger')
        return redirect(url_for('karne.karne_routes.detay', karne_id=karne.id))

    ders_adi = ders_notu.ders_adi
    db.session.delete(ders_notu)
    karne.hesapla_genel_ortalama()
    db.session.commit()

    flash(f'{ders_adi} ders notu silindi.', 'success')
    return redirect(url_for('karne.karne_routes.detay', karne_id=karne.id))


@bp.route('/<int:karne_id>/onayla', methods=['POST'])
@login_required
@role_required('admin')
def onayla(karne_id):
    karne = Karne.query.get_or_404(karne_id)
    if karne.durum == 'taslak':
        karne.durum = 'onaylandi'
        db.session.commit()
        flash('Karne onaylandi.', 'success')
    else:
        flash('Sadece taslak durumundaki karneler onaylanabilir.', 'warning')
    return redirect(url_for('karne.karne_routes.detay', karne_id=karne.id))


@bp.route('/<int:karne_id>/yazdir')
@login_required
@role_required('admin', 'ogretmen')
def yazdir(karne_id):
    karne = Karne.query.get_or_404(karne_id)
    ders_notlari = karne.ders_notlari.order_by(KarneDersNotu.ders_adi).all()

    if karne.durum == 'onaylandi':
        karne.durum = 'basildi'
        db.session.commit()

    return render_template('karne/karne_yazdir.html',
                           karne=karne,
                           ders_notlari=ders_notlari)


@bp.route('/<int:karne_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(karne_id):
    karne = Karne.query.get_or_404(karne_id)
    ogrenci_ad = karne.ogrenci.tam_ad
    db.session.delete(karne)
    db.session.commit()
    flash(f'{ogrenci_ad} icin karne silindi.', 'success')
    return redirect(url_for('karne.karne_routes.liste'))
