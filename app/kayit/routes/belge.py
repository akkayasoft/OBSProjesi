import os
from datetime import date
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, send_from_directory, abort)
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.muhasebe import Ogrenci
from app.models.kayit import OgrenciBelge
from app.kayit.forms import BelgeForm
from app.kayit.routes.ogrenci import _save_belge_dosyasi

bp = Blueprint('belge', __name__)


@bp.route('/<int:ogrenci_id>')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def liste(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    belgeler = OgrenciBelge.query.filter_by(ogrenci_id=ogrenci_id).all()
    return render_template('kayit/belge/liste.html',
                           ogrenci=ogrenci, belgeler=belgeler)


@bp.route('/<int:ogrenci_id>/ekle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def ekle(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    form = BelgeForm()

    if form.validate_on_submit():
        rel_path, orijinal = (None, None)
        if form.dosya.data:
            try:
                rel_path, orijinal = _save_belge_dosyasi(form.dosya.data, 'belgeler')
            except Exception as exc:
                flash(f'Dosya yüklenemedi: {exc}', 'danger')
                return render_template('kayit/belge/belge_form.html',
                                       form=form, ogrenci=ogrenci)

        belge = OgrenciBelge(
            ogrenci_id=ogrenci_id,
            belge_turu=form.belge_turu.data,
            teslim_edildi=form.teslim_edildi.data or bool(rel_path),
            teslim_tarihi=date.today() if (form.teslim_edildi.data or rel_path) else None,
            dosya_yolu=rel_path,
            orijinal_ad=orijinal,
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
@role_required('admin', 'muhasebeci', 'yonetici')
def teslim_toggle(belge_id):
    belge = OgrenciBelge.query.get_or_404(belge_id)
    belge.teslim_edildi = not belge.teslim_edildi
    belge.teslim_tarihi = date.today() if belge.teslim_edildi else None
    db.session.commit()

    durum = 'teslim alındı' if belge.teslim_edildi else 'teslim alınmadı olarak işaretlendi'
    flash(f'{belge.belge_turu_ad} {durum}.', 'success')
    return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=belge.ogrenci_id))


@bp.route('/dosya/<int:belge_id>')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def dosya_indir(belge_id):
    belge = OgrenciBelge.query.get_or_404(belge_id)
    if not belge.dosya_yolu:
        abort(404)

    klasor = current_app.config['UPLOAD_FOLDER']
    full = os.path.join(klasor, belge.dosya_yolu)
    if not os.path.exists(full):
        abort(404)

    download_name = belge.orijinal_ad or os.path.basename(belge.dosya_yolu)
    return send_from_directory(
        klasor,
        belge.dosya_yolu,
        as_attachment=False,
        download_name=download_name,
    )
