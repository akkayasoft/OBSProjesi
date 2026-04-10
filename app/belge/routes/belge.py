from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.utils import role_required
from app.extensions import db
from app.models.belge import Belge
from app.belge.forms import BelgeForm

bp = Blueprint('belge_yonetim', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    page = request.args.get('page', 1, type=int)
    kategori = request.args.get('kategori', '')
    arama = request.args.get('arama', '').strip()

    query = Belge.query.filter_by(aktif=True)
    if kategori:
        query = query.filter(Belge.kategori == kategori)
    if arama:
        query = query.filter(Belge.baslik.ilike(f'%{arama}%'))

    belgeler = query.order_by(Belge.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('belge/belge_listesi.html',
                           belgeler=belgeler, kategori=kategori, arama=arama)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = BelgeForm()
    if form.validate_on_submit():
        belge = Belge(baslik=form.baslik.data, kategori=form.kategori.data,
                      aciklama=form.aciklama.data, erisim=form.erisim.data,
                      aktif=form.aktif.data, yukleyen_id=current_user.id)
        db.session.add(belge)
        db.session.commit()
        flash('Belge eklendi.', 'success')
        return redirect(url_for('belge.belge_yonetim.liste'))
    return render_template('belge/belge_form.html', form=form, baslik='Yeni Belge')


@bp.route('/<int:belge_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(belge_id):
    belge = Belge.query.get_or_404(belge_id)
    form = BelgeForm(obj=belge)
    if form.validate_on_submit():
        belge.baslik = form.baslik.data
        belge.kategori = form.kategori.data
        belge.aciklama = form.aciklama.data
        belge.erisim = form.erisim.data
        belge.aktif = form.aktif.data
        db.session.commit()
        flash('Belge guncellendi.', 'success')
        return redirect(url_for('belge.belge_yonetim.liste'))
    return render_template('belge/belge_form.html', form=form, baslik='Belge Duzenle')


@bp.route('/<int:belge_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(belge_id):
    belge = Belge.query.get_or_404(belge_id)
    db.session.delete(belge)
    db.session.commit()
    flash('Belge silindi.', 'success')
    return redirect(url_for('belge.belge_yonetim.liste'))
