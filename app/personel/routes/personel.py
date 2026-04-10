from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.muhasebe import Personel
from app.personel.forms import PersonelForm, PersonelDuzenleForm

bp = Blueprint('personel_crud', __name__)


@bp.route('/')
@login_required
@role_required('admin',)
def liste():
    arama = request.args.get('arama', '')
    departman = request.args.get('departman', '')
    durum = request.args.get('durum', '')
    page = request.args.get('page', 1, type=int)

    query = Personel.query

    if arama:
        query = query.filter(
            db.or_(
                Personel.ad.ilike(f'%{arama}%'),
                Personel.soyad.ilike(f'%{arama}%'),
                Personel.sicil_no.ilike(f'%{arama}%'),
            )
        )

    if departman:
        query = query.filter(Personel.departman == departman)

    if durum == 'aktif':
        query = query.filter(Personel.aktif == True)
    elif durum == 'pasif':
        query = query.filter(Personel.aktif == False)

    personeller = query.order_by(Personel.ad).paginate(page=page, per_page=20)

    return render_template('personel/personel/liste.html',
                           personeller=personeller,
                           arama=arama,
                           departman=departman,
                           durum=durum)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin',)
def yeni():
    form = PersonelForm()

    if form.validate_on_submit():
        mevcut = Personel.query.filter_by(sicil_no=form.sicil_no.data).first()
        if mevcut:
            flash('Bu sicil numarası zaten kayıtlı!', 'danger')
            return render_template('personel/personel/form.html', form=form, baslik='Yeni Personel')

        personel = Personel(
            sicil_no=form.sicil_no.data,
            tc_kimlik=form.tc_kimlik.data or None,
            ad=form.ad.data,
            soyad=form.soyad.data,
            cinsiyet=form.cinsiyet.data or None,
            dogum_tarihi=form.dogum_tarihi.data,
            telefon=form.telefon.data or None,
            email=form.email.data or None,
            adres=form.adres.data or None,
            pozisyon=form.pozisyon.data or None,
            departman=form.departman.data or None,
            calisma_turu=form.calisma_turu.data,
            maas=form.maas.data,
            ise_baslama_tarihi=form.ise_baslama_tarihi.data,
        )
        db.session.add(personel)
        db.session.commit()
        flash(f'{personel.tam_ad} başarıyla eklendi.', 'success')
        return redirect(url_for('personel.personel_crud.detay', personel_id=personel.id))

    return render_template('personel/personel/form.html', form=form, baslik='Yeni Personel')


@bp.route('/<int:personel_id>')
@login_required
@role_required('admin',)
def detay(personel_id):
    personel = Personel.query.get_or_404(personel_id)
    izinler = personel.izinler.order_by(db.desc('baslangic_tarihi')).all()
    odemeler = personel.odeme_kayitlari.order_by(db.desc('tarih')).limit(20).all()
    return render_template('personel/personel/detay.html',
                           personel=personel,
                           izinler=izinler,
                           odemeler=odemeler)


@bp.route('/<int:personel_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin',)
def duzenle(personel_id):
    personel = Personel.query.get_or_404(personel_id)
    form = PersonelDuzenleForm(obj=personel)

    if form.validate_on_submit():
        # Sicil no değiştiyse kontrol et
        if form.sicil_no.data != personel.sicil_no:
            mevcut = Personel.query.filter_by(sicil_no=form.sicil_no.data).first()
            if mevcut:
                flash('Bu sicil numarası zaten kayıtlı!', 'danger')
                return render_template('personel/personel/form.html',
                                       form=form, baslik='Personel Düzenle')

        personel.sicil_no = form.sicil_no.data
        personel.tc_kimlik = form.tc_kimlik.data or None
        personel.ad = form.ad.data
        personel.soyad = form.soyad.data
        personel.cinsiyet = form.cinsiyet.data or None
        personel.dogum_tarihi = form.dogum_tarihi.data
        personel.telefon = form.telefon.data or None
        personel.email = form.email.data or None
        personel.adres = form.adres.data or None
        personel.pozisyon = form.pozisyon.data or None
        personel.departman = form.departman.data or None
        personel.calisma_turu = form.calisma_turu.data
        personel.maas = form.maas.data
        personel.ise_baslama_tarihi = form.ise_baslama_tarihi.data
        personel.ise_bitis_tarihi = form.ise_bitis_tarihi.data

        db.session.commit()
        flash('Personel bilgileri güncellendi.', 'success')
        return redirect(url_for('personel.personel_crud.detay', personel_id=personel.id))

    return render_template('personel/personel/form.html',
                           form=form, baslik='Personel Düzenle')


@bp.route('/<int:personel_id>/durum', methods=['POST'])
@login_required
@role_required('admin',)
def durum_degistir(personel_id):
    personel = Personel.query.get_or_404(personel_id)
    personel.aktif = not personel.aktif
    db.session.commit()
    durum_str = 'aktif' if personel.aktif else 'pasif'
    flash(f'{personel.tam_ad} {durum_str} yapıldı.', 'success')
    return redirect(url_for('personel.personel_crud.detay', personel_id=personel.id))
