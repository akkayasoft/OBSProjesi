from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.servis import Guzergah, ServisDurak
from app.servis.forms import DurakForm

bp = Blueprint('durak', __name__)


@bp.route('/guzergah/<int:guzergah_id>/durak/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni(guzergah_id):
    guzergah = Guzergah.query.get_or_404(guzergah_id)
    form = DurakForm()

    # Varsayilan sira numarasi
    if not form.sira.data:
        son_durak = ServisDurak.query.filter_by(
            guzergah_id=guzergah.id
        ).order_by(ServisDurak.sira.desc()).first()
        form.sira.data = (son_durak.sira + 1) if son_durak else 1

    if form.validate_on_submit():
        durak = ServisDurak(
            guzergah_id=guzergah.id,
            ad=form.ad.data,
            sira=form.sira.data,
            tahmini_varis=form.tahmini_varis.data,
            adres=form.adres.data,
        )
        db.session.add(durak)
        db.session.commit()
        flash('Durak basariyla eklendi.', 'success')
        return redirect(url_for('servis.guzergah.detay', guzergah_id=guzergah.id))

    return render_template('servis/durak_form.html',
                           form=form, baslik='Yeni Durak',
                           guzergah=guzergah)


@bp.route('/durak/<int:durak_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(durak_id):
    durak = ServisDurak.query.get_or_404(durak_id)
    form = DurakForm(obj=durak)

    if form.validate_on_submit():
        durak.ad = form.ad.data
        durak.sira = form.sira.data
        durak.tahmini_varis = form.tahmini_varis.data
        durak.adres = form.adres.data
        db.session.commit()
        flash('Durak basariyla guncellendi.', 'success')
        return redirect(url_for('servis.guzergah.detay', guzergah_id=durak.guzergah_id))

    return render_template('servis/durak_form.html',
                           form=form, baslik='Durak Duzenle',
                           guzergah=durak.guzergah)


@bp.route('/durak/<int:durak_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(durak_id):
    durak = ServisDurak.query.get_or_404(durak_id)
    guzergah_id = durak.guzergah_id
    db.session.delete(durak)
    db.session.commit()
    flash('Durak basariyla silindi.', 'success')
    return redirect(url_for('servis.guzergah.detay', guzergah_id=guzergah_id))
