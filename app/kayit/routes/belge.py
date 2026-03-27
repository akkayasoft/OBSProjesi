from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.extensions import db
from app.models.muhasebe import Ogrenci
from app.models.kayit import OgrenciBelge
from app.kayit.forms import BelgeForm

bp = Blueprint('belge', __name__)


@bp.route('/<int:ogrenci_id>')
@login_required
def liste(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    belgeler = OgrenciBelge.query.filter_by(ogrenci_id=ogrenci_id).all()
    return render_template('kayit/belge/liste.html',
                           ogrenci=ogrenci, belgeler=belgeler)


@bp.route('/<int:ogrenci_id>/ekle', methods=['GET', 'POST'])
@login_required
def ekle(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    form = BelgeForm()

    if form.validate_on_submit():
        belge = OgrenciBelge(
            ogrenci_id=ogrenci_id,
            belge_turu=form.belge_turu.data,
            teslim_edildi=form.teslim_edildi.data,
            teslim_tarihi=date.today() if form.teslim_edildi.data else None,
            aciklama=form.aciklama.data
        )
        db.session.add(belge)
        db.session.commit()
        flash('Belge kaydı eklendi.', 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    return render_template('kayit/belge/belge_form.html',
                           form=form, ogrenci=ogrenci)


@bp.route('/teslim/<int:belge_id>', methods=['POST'])
@login_required
def teslim_toggle(belge_id):
    belge = OgrenciBelge.query.get_or_404(belge_id)
    belge.teslim_edildi = not belge.teslim_edildi
    belge.teslim_tarihi = date.today() if belge.teslim_edildi else None
    db.session.commit()

    durum = 'teslim alındı' if belge.teslim_edildi else 'teslim alınmadı olarak işaretlendi'
    flash(f'{belge.belge_turu_ad} {durum}.', 'success')
    return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=belge.ogrenci_id))
