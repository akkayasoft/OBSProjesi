from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.servis import Arac, Guzergah
from app.servis.forms import AracForm

bp = Blueprint('arac', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    araclar = Arac.query.filter_by(aktif=True).order_by(
        Arac.plaka
    ).paginate(page=page, per_page=12)

    return render_template('servis/arac_listesi.html',
                           araclar=araclar)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = AracForm()
    guzergahlar = Guzergah.query.filter_by(aktif=True).order_by(Guzergah.ad).all()
    form.guzergah_id.choices = [(0, 'Seciniz')] + [(g.id, f'{g.kod} - {g.ad}') for g in guzergahlar]

    if form.validate_on_submit():
        arac = Arac(
            plaka=form.plaka.data,
            marka=form.marka.data,
            model=form.model.data,
            kapasite=form.kapasite.data,
            sofor_adi=form.sofor_adi.data,
            sofor_telefon=form.sofor_telefon.data,
            guzergah_id=form.guzergah_id.data if form.guzergah_id.data != 0 else None,
            aktif=form.aktif.data,
        )
        db.session.add(arac)
        db.session.commit()
        flash('Arac basariyla eklendi.', 'success')
        return redirect(url_for('servis.arac.liste'))

    return render_template('servis/arac_form.html',
                           form=form, baslik='Yeni Arac')


@bp.route('/<int:arac_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(arac_id):
    arac = Arac.query.get_or_404(arac_id)
    form = AracForm(obj=arac)
    guzergahlar = Guzergah.query.filter_by(aktif=True).order_by(Guzergah.ad).all()
    form.guzergah_id.choices = [(0, 'Seciniz')] + [(g.id, f'{g.kod} - {g.ad}') for g in guzergahlar]

    if form.validate_on_submit():
        arac.plaka = form.plaka.data
        arac.marka = form.marka.data
        arac.model = form.model.data
        arac.kapasite = form.kapasite.data
        arac.sofor_adi = form.sofor_adi.data
        arac.sofor_telefon = form.sofor_telefon.data
        arac.guzergah_id = form.guzergah_id.data if form.guzergah_id.data != 0 else None
        arac.aktif = form.aktif.data
        db.session.commit()
        flash('Arac basariyla guncellendi.', 'success')
        return redirect(url_for('servis.arac.liste'))

    return render_template('servis/arac_form.html',
                           form=form, baslik='Arac Duzenle')


@bp.route('/<int:arac_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(arac_id):
    arac = Arac.query.get_or_404(arac_id)
    db.session.delete(arac)
    db.session.commit()
    flash('Arac basariyla silindi.', 'success')
    return redirect(url_for('servis.arac.liste'))
