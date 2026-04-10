from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.muhasebe import Personel
from app.models.personel import PersonelIzin
from app.personel.forms import IzinForm

bp = Blueprint('izin', __name__)


@bp.route('/')
@login_required
@role_required('admin',)
def liste():
    personel_id = request.args.get('personel_id', 0, type=int)
    izin_turu = request.args.get('izin_turu', '')
    durum = request.args.get('durum', '')
    page = request.args.get('page', 1, type=int)

    query = PersonelIzin.query.join(Personel)

    if personel_id:
        query = query.filter(PersonelIzin.personel_id == personel_id)

    if izin_turu:
        query = query.filter(PersonelIzin.izin_turu == izin_turu)

    if durum:
        query = query.filter(PersonelIzin.durum == durum)

    izinler = query.order_by(PersonelIzin.baslangic_tarihi.desc()).paginate(page=page, per_page=20)
    personeller = Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()

    return render_template('personel/izin/liste.html',
                           izinler=izinler,
                           personeller=personeller,
                           personel_id=personel_id,
                           izin_turu=izin_turu,
                           durum=durum)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin',)
def yeni():
    form = IzinForm()
    personeller = Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    form.personel_id.choices = [(p.id, f'{p.tam_ad} ({p.sicil_no})') for p in personeller]

    # URL'den gelen personel_id
    personel_id = request.args.get('personel_id', 0, type=int)
    if request.method == 'GET' and personel_id:
        form.personel_id.data = personel_id

    if form.validate_on_submit():
        if form.bitis_tarihi.data < form.baslangic_tarihi.data:
            flash('Bitiş tarihi başlangıç tarihinden önce olamaz!', 'danger')
            return render_template('personel/izin/form.html', form=form, baslik='Yeni İzin Talebi')

        gun_sayisi = (form.bitis_tarihi.data - form.baslangic_tarihi.data).days + 1

        izin = PersonelIzin(
            personel_id=form.personel_id.data,
            izin_turu=form.izin_turu.data,
            baslangic_tarihi=form.baslangic_tarihi.data,
            bitis_tarihi=form.bitis_tarihi.data,
            gun_sayisi=gun_sayisi,
            durum='beklemede',
            aciklama=form.aciklama.data or None,
            olusturan_id=current_user.id,
        )
        db.session.add(izin)
        db.session.commit()

        personel = Personel.query.get(form.personel_id.data)
        flash(f'{personel.tam_ad} için {gun_sayisi} günlük izin talebi oluşturuldu.', 'success')
        return redirect(url_for('personel.izin.liste'))

    return render_template('personel/izin/form.html', form=form, baslik='Yeni İzin Talebi')


@bp.route('/<int:izin_id>/onayla', methods=['POST'])
@login_required
@role_required('admin',)
def onayla(izin_id):
    izin = PersonelIzin.query.get_or_404(izin_id)
    if izin.durum != 'beklemede':
        flash('Bu izin talebi zaten işlenmiş!', 'warning')
        return redirect(url_for('personel.izin.liste'))

    izin.durum = 'onaylandi'
    izin.onaylayan_id = current_user.id
    db.session.commit()
    flash(f'{izin.personel.tam_ad} için izin onaylandı.', 'success')
    return redirect(url_for('personel.izin.liste'))


@bp.route('/<int:izin_id>/reddet', methods=['POST'])
@login_required
@role_required('admin',)
def reddet(izin_id):
    izin = PersonelIzin.query.get_or_404(izin_id)
    if izin.durum != 'beklemede':
        flash('Bu izin talebi zaten işlenmiş!', 'warning')
        return redirect(url_for('personel.izin.liste'))

    izin.durum = 'reddedildi'
    izin.onaylayan_id = current_user.id
    db.session.commit()
    flash(f'{izin.personel.tam_ad} için izin reddedildi.', 'info')
    return redirect(url_for('personel.izin.liste'))


@bp.route('/<int:izin_id>/iptal', methods=['POST'])
@login_required
@role_required('admin',)
def iptal(izin_id):
    izin = PersonelIzin.query.get_or_404(izin_id)
    db.session.delete(izin)
    db.session.commit()
    flash('İzin kaydı silindi.', 'success')
    return redirect(url_for('personel.izin.liste'))
