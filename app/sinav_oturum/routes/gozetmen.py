from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.sinav_oturum import SinavOturum, SinavGozetmen
from app.models.muhasebe import Personel
from app.sinav_oturum.forms import GozetmenForm

bp = Blueprint('gozetmen', __name__)


@bp.route('/<int:oturum_id>/ata', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def ata(oturum_id):
    oturum = SinavOturum.query.get_or_404(oturum_id)
    form = GozetmenForm()

    # Mevcut gozetmen id'lerini al
    mevcut_ids = [g.ogretmen_id for g in oturum.gozetmenler.all()]

    # Sadece henuz atanmamis ogretmenleri goster
    ogretmenler = Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    form.ogretmen_id.choices = [
        (p.id, f'{p.sicil_no} - {p.tam_ad}')
        for p in ogretmenler if p.id not in mevcut_ids
    ]

    if not form.ogretmen_id.choices:
        flash('Atanabilecek baska ogretmen bulunmuyor.', 'warning')
        return redirect(url_for('sinav_oturum.oturum.detay', oturum_id=oturum.id))

    if form.validate_on_submit():
        gozetmen = SinavGozetmen(
            sinav_oturum_id=oturum.id,
            ogretmen_id=form.ogretmen_id.data,
            gorev=form.gorev.data,
        )
        db.session.add(gozetmen)
        db.session.commit()
        flash('Gozetmen basariyla atandi.', 'success')
        return redirect(url_for('sinav_oturum.oturum.detay', oturum_id=oturum.id))

    return render_template('sinav_oturum/gozetmen_form.html',
                           form=form, oturum=oturum)


@bp.route('/<int:oturum_id>/kaldir/<int:gozetmen_id>', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def kaldir(oturum_id, gozetmen_id):
    gozetmen = SinavGozetmen.query.get_or_404(gozetmen_id)
    if gozetmen.sinav_oturum_id != oturum_id:
        flash('Gecersiz islem.', 'danger')
        return redirect(url_for('sinav_oturum.oturum.liste'))

    db.session.delete(gozetmen)
    db.session.commit()
    flash('Gozetmen basariyla kaldirildi.', 'success')
    return redirect(url_for('sinav_oturum.oturum.detay', oturum_id=oturum_id))
