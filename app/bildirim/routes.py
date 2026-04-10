from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.bildirim import Bildirim
from app.bildirim import bildirim_bp


@bildirim_bp.route('/')
@login_required
def liste():
    filtre = request.args.get('filtre', 'tumu')
    page = request.args.get('page', 1, type=int)

    query = Bildirim.query.filter_by(kullanici_id=current_user.id)

    if filtre == 'okunmamis':
        query = query.filter_by(okundu=False)

    bildirimler = query.order_by(
        Bildirim.created_at.desc()
    ).paginate(page=page, per_page=20)

    return render_template('bildirim/liste.html',
                           bildirimler=bildirimler,
                           filtre=filtre)


@bildirim_bp.route('/<int:id>/oku', methods=['POST'])
@login_required
def oku(id):
    bildirim = Bildirim.query.filter_by(id=id, kullanici_id=current_user.id).first_or_404()
    bildirim.okundu = True
    bildirim.okunma_tarihi = datetime.utcnow()
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'okunmamis': Bildirim.okunmamis_sayisi(current_user.id)})

    flash('Bildirim okundu olarak işaretlendi.', 'success')
    return redirect(url_for('bildirim.liste'))


@bildirim_bp.route('/tumunu-oku', methods=['POST'])
@login_required
def tumunu_oku():
    Bildirim.query.filter_by(
        kullanici_id=current_user.id,
        okundu=False
    ).update({
        'okundu': True,
        'okunma_tarihi': datetime.utcnow()
    })
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'okunmamis': 0})

    flash('Tüm bildirimler okundu olarak işaretlendi.', 'success')
    return redirect(url_for('bildirim.liste'))


@bildirim_bp.route('/<int:id>/sil', methods=['POST'])
@login_required
def sil(id):
    bildirim = Bildirim.query.filter_by(id=id, kullanici_id=current_user.id).first_or_404()
    db.session.delete(bildirim)
    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'okunmamis': Bildirim.okunmamis_sayisi(current_user.id)})

    flash('Bildirim silindi.', 'success')
    return redirect(url_for('bildirim.liste'))


@bildirim_bp.route('/api/sayac')
@login_required
def api_sayac():
    return jsonify({
        'okunmamis': Bildirim.okunmamis_sayisi(current_user.id)
    })
