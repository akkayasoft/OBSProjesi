import os
import uuid
from datetime import date
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, session, send_from_directory, abort)
from flask_login import login_required
from werkzeug.utils import secure_filename
from app.utils import role_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.muhasebe import Ogrenci
from app.models.kayit import (
    Sinif, Sube, KayitDonemi, OgrenciKayit, VeliBilgisi, OgrenciBelge
)
from app.kayit.forms import (
    OgrenciKayitForm, OgrenciDuzenleForm, DurumDegistirForm, VeliForm,
    KarteksYukleForm
)

bp = Blueprint('ogrenci', __name__)


def _save_belge_dosyasi(file_storage, alt_klasor: str) -> tuple[str, str]:
    """
    Yüklenen dosyayı `instance/uploads/<alt_klasor>/` altına kaydeder.
    Geri dönüş: (relative_path, original_filename).
    """
    klasor = os.path.join(current_app.config['UPLOAD_FOLDER'], alt_klasor)
    os.makedirs(klasor, exist_ok=True)

    orijinal = secure_filename(file_storage.filename or 'belge')
    uzanti = os.path.splitext(orijinal)[1].lower() or '.bin'
    yeni_ad = f"{uuid.uuid4().hex}{uzanti}"
    tam_yol = os.path.join(klasor, yeni_ad)
    file_storage.save(tam_yol)

    # DB'ye `instance/uploads/` köküne göre relative path kaydedelim
    rel = os.path.join(alt_klasor, yeni_ad)
    return rel, orijinal


@bp.route('/')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def liste():
    page = request.args.get('page', 1, type=int)
    arama = request.args.get('q', '')
    sinif_filtre = request.args.get('sinif', 0, type=int)
    durum_filtre = request.args.get('durum', '')

    query = Ogrenci.query.filter_by(aktif=True)
    kayit_joined = False

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
        if not kayit_joined:
            query = query.join(OgrenciKayit)
            kayit_joined = True
        query = query.join(Sube).filter(
            Sube.sinif_id == sinif_filtre,
            OgrenciKayit.durum == 'aktif'
        )

    if durum_filtre:
        if not kayit_joined:
            query = query.join(OgrenciKayit)
            kayit_joined = True
        query = query.filter(OgrenciKayit.durum == durum_filtre)

    if kayit_joined:
        query = query.distinct()

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


@bp.route('/karteks-yukle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def karteks_yukle():
    """
    Karteks görselini yükler, geçici olarak session'a koyar ve yeni kayıt
    sayfasına yönlendirir. Yeni kayıt sayfası karteksi yan panelde gösterir,
    kullanıcı bilgileri görüntüye bakarak elle doldurur. Form kaydedilince
    karteks oluşturulan öğrenciye belge olarak bağlanır.
    """
    form = KarteksYukleForm()
    if form.validate_on_submit():
        try:
            rel_path, orijinal = _save_belge_dosyasi(form.karteks.data, 'karteks')
        except Exception as exc:
            flash(f'Dosya kaydedilemedi: {exc}', 'danger')
            return render_template('kayit/ogrenci/karteks_yukle.html', form=form)

        session['karteks_dosya'] = {'rel': rel_path, 'orijinal': orijinal}
        flash(
            'Karteks yüklendi. Sağdaki forma karteks görüntüsüne bakarak '
            'bilgileri doldurun.',
            'success'
        )
        return redirect(url_for('kayit.ogrenci.yeni_kayit'))

    return render_template('kayit/ogrenci/karteks_yukle.html', form=form)


@bp.route('/karteks-onizleme')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def karteks_onizleme():
    """Yeni kayıt akışında session'daki karteks görselini serve eder."""
    karteks = session.get('karteks_dosya')
    if not karteks:
        abort(404)

    klasor = current_app.config['UPLOAD_FOLDER']
    full = os.path.join(klasor, karteks['rel'])
    if not os.path.exists(full):
        abort(404)

    return send_from_directory(klasor, karteks['rel'], as_attachment=False)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def yeni_kayit():
    # Karteks varsa yan panelde göstereceğiz, kayıt sonunda öğrenciye bağlayacağız
    karteks_dosya = session.get('karteks_dosya')

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
                                   form=form, baslik='Yeni Öğrenci Kaydı',
                                   karteks_aktif=bool(karteks_dosya),
                                   karteks_dosya=karteks_dosya)

        # Kontenjan kontrolü
        sube = Sube.query.get(form.sube_id.data)
        if sube and sube.bos_kontenjan <= 0:
            flash(f'{sube.tam_ad} kontenjanı dolu.', 'danger')
            return render_template('kayit/ogrenci/kayit_form.html',
                                   form=form, baslik='Yeni Öğrenci Kaydı',
                                   karteks_aktif=bool(karteks_dosya),
                                   karteks_dosya=karteks_dosya)

        # Otomatik kullanıcı hesabı oluştur (username = öğrenci no)
        username = form.ogrenci_no.data
        varsayilan_sifre = form.tc_kimlik.data if form.tc_kimlik.data else form.ogrenci_no.data
        user = User(
            username=username,
            email=form.email.data or f"{username}@ogrenci.obs",
            ad=form.ad.data,
            soyad=form.soyad.data,
            rol='ogrenci',
            aktif=True
        )
        user.set_password(varsayilan_sifre)
        db.session.add(user)
        db.session.flush()

        ogrenci = Ogrenci(
            user_id=user.id,
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

        # Karteks ile gelmişse dosyayı belge olarak kaydet
        if karteks_dosya:
            db.session.add(OgrenciBelge(
                ogrenci_id=ogrenci.id,
                belge_turu='karteks',
                teslim_edildi=True,
                teslim_tarihi=date.today(),
                dosya_yolu=karteks_dosya.get('rel'),
                orijinal_ad=karteks_dosya.get('orijinal'),
                aciklama='Kayıt sırasında karteks olarak yüklendi.'
            ))

        db.session.commit()

        # Karteks session'ını temizle
        session.pop('karteks_dosya', None)

        flash(f'{ogrenci.tam_ad} başarıyla kaydedildi. '
              f'Giriş bilgileri — Kullanıcı adı: {username}, Şifre: {varsayilan_sifre}', 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci.id))

    return render_template('kayit/ogrenci/kayit_form.html',
                           form=form, baslik='Yeni Öğrenci Kaydı',
                           karteks_aktif=bool(karteks_dosya),
                           karteks_dosya=karteks_dosya)


@bp.route('/karteks-iptal', methods=['POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def karteks_iptal():
    """Session'daki karteks görselini ve geçici dosyayı temizler."""
    karteks_dosya = session.pop('karteks_dosya', None)
    if karteks_dosya:
        try:
            full = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                karteks_dosya['rel'])
            if os.path.exists(full):
                os.remove(full)
        except OSError:
            pass
    flash('Karteks kaldırıldı.', 'info')
    return redirect(url_for('kayit.ogrenci.yeni_kayit'))


@bp.route('/<int:ogrenci_id>')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
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
@role_required('admin', 'muhasebeci', 'yonetici')
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
@role_required('admin', 'muhasebeci', 'yonetici')
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
@role_required('admin', 'muhasebeci', 'yonetici')
def veli_ekle(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    form = VeliForm()

    if form.validate_on_submit():
        # Otomatik veli kullanıcı hesabı oluştur
        # Username: veli_<ogrenci_no>_<yakinlik> (ör: veli_1001_anne)
        username = f"veli_{ogrenci.ogrenci_no}_{form.yakinlik.data}"
        varsayilan_sifre = form.tc_kimlik.data if form.tc_kimlik.data else username
        user = User(
            username=username,
            email=form.email.data or f"{username}@veli.obs",
            ad=form.ad.data,
            soyad=form.soyad.data,
            rol='veli',
            aktif=True
        )
        user.set_password(varsayilan_sifre)
        db.session.add(user)
        db.session.flush()

        veli = VeliBilgisi(
            user_id=user.id,
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
        flash(f'Veli bilgisi başarıyla eklendi. '
              f'Giriş bilgileri — Kullanıcı adı: {username}, Şifre: {varsayilan_sifre}', 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    return render_template('kayit/ogrenci/veli_form.html',
                           form=form, ogrenci=ogrenci, baslik='Veli Ekle')
