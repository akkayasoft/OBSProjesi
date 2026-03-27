from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.muhasebe import Ogrenci
from app.models.kayit import (
    Sinif, Sube, KayitDonemi, OgrenciKayit, VeliBilgisi, OgrenciBelge
)
from app.kayit.forms import (
    OgrenciKayitForm, OgrenciDuzenleForm, DurumDegistirForm, VeliForm
)

bp = Blueprint('ogrenci', __name__)


@bp.route('/')
@login_required
def liste():
    page = request.args.get('page', 1, type=int)
    arama = request.args.get('q', '')
    sinif_filtre = request.args.get('sinif', 0, type=int)
    durum_filtre = request.args.get('durum', '')

    query = Ogrenci.query.filter_by(aktif=True)

    if arama:
        query = query.filter(
            db.or_(
                Ogrenci.ad.ilike(f'%{arama}%'),
                Ogrenci.soyad.ilike(f'%{arama}%'),
                Ogrenci.ogrenci_no.ilike(f'%{arama}%'),
                Ogrenci.tc_kimlik.ilike(f'%{arama}%')
            )
        )

    if sinif_filtre:
        query = query.join(OgrenciKayit).join(Sube).filter(
            Sube.sinif_id == sinif_filtre,
            OgrenciKayit.durum == 'aktif'
        )

    ogrenciler = query.order_by(Ogrenci.soyad, Ogrenci.ad).paginate(
        page=page, per_page=20, error_out=False
    )

    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.seviye).all()

    return render_template('kayit/ogrenci/liste.html',
                           ogrenciler=ogrenciler,
                           siniflar=siniflar,
                           arama=arama,
                           sinif_filtre=sinif_filtre,
                           durum_filtre=durum_filtre)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
def yeni_kayit():
    form = OgrenciKayitForm()

    donemler = KayitDonemi.query.filter_by(aktif=True).all()
    form.donem_id.choices = [(d.id, d.ad) for d in donemler]

    subeler = Sube.query.filter_by(aktif=True).join(Sinif).order_by(Sinif.seviye, Sube.ad).all()
    form.sube_id.choices = [(s.id, s.tam_ad) for s in subeler]

    if form.validate_on_submit():
        # Öğrenci no kontrolü
        mevcut = Ogrenci.query.filter_by(ogrenci_no=form.ogrenci_no.data).first()
        if mevcut:
            flash('Bu öğrenci numarası zaten kayıtlı.', 'danger')
            return render_template('kayit/ogrenci/kayit_form.html',
                                   form=form, baslik='Yeni Öğrenci Kaydı')

        # Kontenjan kontrolü
        sube = Sube.query.get(form.sube_id.data)
        if sube and sube.bos_kontenjan <= 0:
            flash(f'{sube.tam_ad} kontenjanı dolu.', 'danger')
            return render_template('kayit/ogrenci/kayit_form.html',
                                   form=form, baslik='Yeni Öğrenci Kaydı')

        ogrenci = Ogrenci(
            ogrenci_no=form.ogrenci_no.data,
            tc_kimlik=form.tc_kimlik.data or None,
            ad=form.ad.data,
            soyad=form.soyad.data,
            cinsiyet=form.cinsiyet.data or None,
            dogum_tarihi=form.dogum_tarihi.data,
            dogum_yeri=form.dogum_yeri.data or None,
            kan_grubu=form.kan_grubu.data or None,
            telefon=form.telefon.data or None,
            email=form.email.data or None,
            adres=form.adres.data or None,
            sinif=sube.sinif.ad if sube else None
        )
        db.session.add(ogrenci)
        db.session.flush()

        # Kayıt kaydı oluştur
        kayit = OgrenciKayit(
            ogrenci_id=ogrenci.id,
            donem_id=form.donem_id.data,
            sube_id=form.sube_id.data,
            kayit_tarihi=date.today(),
            durum='aktif',
            olusturan_id=current_user.id
        )
        db.session.add(kayit)

        # Varsayılan belge kayıtları oluştur
        varsayilan_belgeler = [
            'nufus_cuzdani', 'ogrenim_belgesi', 'fotograf',
            'saglik_raporu', 'ikametgah'
        ]
        for belge_turu in varsayilan_belgeler:
            db.session.add(OgrenciBelge(
                ogrenci_id=ogrenci.id,
                belge_turu=belge_turu,
                teslim_edildi=False
            ))

        db.session.commit()
        flash(f'{ogrenci.tam_ad} başarıyla kaydedildi.', 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci.id))

    return render_template('kayit/ogrenci/kayit_form.html',
                           form=form, baslik='Yeni Öğrenci Kaydı')


@bp.route('/<int:ogrenci_id>')
@login_required
def detay(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    kayitlar = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci_id
    ).order_by(OgrenciKayit.kayit_tarihi.desc()).all()

    veliler = VeliBilgisi.query.filter_by(ogrenci_id=ogrenci_id).all()
    belgeler = OgrenciBelge.query.filter_by(ogrenci_id=ogrenci_id).all()

    aktif_kayit = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci_id, durum='aktif'
    ).first()

    return render_template('kayit/ogrenci/detay.html',
                           ogrenci=ogrenci,
                           kayitlar=kayitlar,
                           veliler=veliler,
                           belgeler=belgeler,
                           aktif_kayit=aktif_kayit)


@bp.route('/<int:ogrenci_id>/duzenle', methods=['GET', 'POST'])
@login_required
def duzenle(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    form = OgrenciDuzenleForm(obj=ogrenci)

    if form.validate_on_submit():
        ogrenci.ogrenci_no = form.ogrenci_no.data
        ogrenci.tc_kimlik = form.tc_kimlik.data or None
        ogrenci.ad = form.ad.data
        ogrenci.soyad = form.soyad.data
        ogrenci.cinsiyet = form.cinsiyet.data or None
        ogrenci.dogum_tarihi = form.dogum_tarihi.data
        ogrenci.dogum_yeri = form.dogum_yeri.data or None
        ogrenci.kan_grubu = form.kan_grubu.data or None
        ogrenci.telefon = form.telefon.data or None
        ogrenci.email = form.email.data or None
        ogrenci.adres = form.adres.data or None

        db.session.commit()
        flash('Öğrenci bilgileri güncellendi.', 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    return render_template('kayit/ogrenci/duzenle.html',
                           form=form, ogrenci=ogrenci)


@bp.route('/<int:ogrenci_id>/durum', methods=['GET', 'POST'])
@login_required
def durum_degistir(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    aktif_kayit = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci_id, durum='aktif'
    ).first()

    if not aktif_kayit:
        flash('Bu öğrencinin aktif kaydı bulunmuyor.', 'warning')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    form = DurumDegistirForm()

    if form.validate_on_submit():
        aktif_kayit.durum = form.durum.data
        aktif_kayit.durum_tarihi = date.today()
        aktif_kayit.durum_aciklama = form.aciklama.data

        if form.durum.data in ('mezun', 'nakil_giden', 'kayit_silindi'):
            ogrenci.aktif = False

        db.session.commit()
        label, _ = aktif_kayit.durum_badge
        flash(f'Öğrenci durumu "{label}" olarak güncellendi.', 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    return render_template('kayit/ogrenci/durum_degistir.html',
                           form=form, ogrenci=ogrenci, aktif_kayit=aktif_kayit)


@bp.route('/<int:ogrenci_id>/veli-ekle', methods=['GET', 'POST'])
@login_required
def veli_ekle(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    form = VeliForm()

    if form.validate_on_submit():
        veli = VeliBilgisi(
            ogrenci_id=ogrenci_id,
            yakinlik=form.yakinlik.data,
            tc_kimlik=form.tc_kimlik.data or None,
            ad=form.ad.data,
            soyad=form.soyad.data,
            telefon=form.telefon.data or None,
            email=form.email.data or None,
            meslek=form.meslek.data or None,
            adres=form.adres.data or None
        )
        db.session.add(veli)

        # Ogrenci tablosundaki veli bilgisini de güncelle
        if not ogrenci.veli_ad:
            ogrenci.veli_ad = f"{form.ad.data} {form.soyad.data}"
            ogrenci.veli_telefon = form.telefon.data

        db.session.commit()
        flash('Veli bilgisi başarıyla eklendi.', 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    return render_template('kayit/ogrenci/veli_form.html',
                           form=form, ogrenci=ogrenci, baslik='Veli Ekle')
