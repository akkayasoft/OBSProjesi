"""Sinav icindeki ders bloklarinin CRUD."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required

from app.utils import role_required
from app.extensions import db
from app.models.deneme_sinavi import DenemeSinavi, DenemeDersi
from app.deneme_sinavi.forms import DenemeDersiForm


bp = Blueprint('ders', __name__, url_prefix='/sinav/<int:sinav_id>/ders')


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni(sinav_id):
    sinav = DenemeSinavi.query.get_or_404(sinav_id)
    form = DenemeDersiForm()
    if form.validate_on_submit():
        ders = DenemeDersi(
            deneme_sinavi_id=sinav.id,
            ders_kodu=form.ders_kodu.data.lower().strip(),
            ders_adi=form.ders_adi.data,
            soru_sayisi=form.soru_sayisi.data,
            katsayi=form.katsayi.data,
            alan=(form.alan.data or None),
            sira=form.sira.data or 0,
        )
        db.session.add(ders)
        db.session.commit()
        flash(f'Ders blogu eklendi: {ders.ders_adi}', 'success')
        return redirect(url_for('deneme_sinavi.sinav.detay', sinav_id=sinav.id))
    return render_template('deneme_sinavi/ders_form.html',
                           form=form, sinav=sinav, baslik='Yeni Ders Blogu')


@bp.route('/<int:ders_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(sinav_id, ders_id):
    sinav = DenemeSinavi.query.get_or_404(sinav_id)
    ders = DenemeDersi.query.get_or_404(ders_id)
    if ders.deneme_sinavi_id != sinav.id:
        flash('Bu ders bu sinava ait degil.', 'danger')
        return redirect(url_for('deneme_sinavi.sinav.detay', sinav_id=sinav.id))

    form = DenemeDersiForm(obj=ders)
    if form.validate_on_submit():
        ders.ders_kodu = form.ders_kodu.data.lower().strip()
        ders.ders_adi = form.ders_adi.data
        ders.soru_sayisi = form.soru_sayisi.data
        ders.katsayi = form.katsayi.data
        ders.alan = form.alan.data or None
        ders.sira = form.sira.data or 0
        db.session.commit()
        flash('Ders blogu guncellendi.', 'success')
        return redirect(url_for('deneme_sinavi.sinav.detay', sinav_id=sinav.id))
    return render_template('deneme_sinavi/ders_form.html',
                           form=form, sinav=sinav, ders=ders,
                           baslik=f'Duzenle: {ders.ders_adi}')


@bp.route('/<int:ders_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(sinav_id, ders_id):
    sinav = DenemeSinavi.query.get_or_404(sinav_id)
    ders = DenemeDersi.query.get_or_404(ders_id)
    if ders.deneme_sinavi_id != sinav.id:
        flash('Bu ders bu sinava ait degil.', 'danger')
    else:
        db.session.delete(ders)
        db.session.commit()
        flash(f'"{ders.ders_adi}" silindi.', 'success')
    return redirect(url_for('deneme_sinavi.sinav.detay', sinav_id=sinav.id))
