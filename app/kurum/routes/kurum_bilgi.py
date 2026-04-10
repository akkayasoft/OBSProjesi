from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.kurum import Kurum
from app.kurum.forms import KurumForm

bp = Blueprint('kurum_bilgi', __name__)


@bp.route('/bilgi')
@login_required
@role_required('admin')
def goruntule():
    kurum = Kurum.query.first()
    return render_template('kurum/kurum_bilgi.html', kurum=kurum)


@bp.route('/bilgi/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle():
    kurum = Kurum.query.first()
    if not kurum:
        kurum = Kurum(ad='', kurum_turu='lise')
        db.session.add(kurum)
        db.session.commit()

    form = KurumForm(obj=kurum)

    if form.validate_on_submit():
        form.populate_obj(kurum)
        db.session.commit()
        flash('Kurum bilgileri basariyla guncellendi.', 'success')
        return redirect(url_for('kurum.kurum_bilgi.goruntule'))

    return render_template('kurum/kurum_form.html', form=form, kurum=kurum)
