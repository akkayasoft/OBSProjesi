from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.ayarlar import SistemAyar
from app.extensions import db

bp = Blueprint('iletisim_ayar', __name__)


@bp.route('/iletisim', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def index():
    if request.method == 'POST':
        anahtarlar = ['sms_saglayici', 'bildirim_email', 'otomatik_bildirim']
        for anahtar in anahtarlar:
            deger = request.form.get(anahtar, '')
            if anahtar == 'otomatik_bildirim':
                deger = 'true' if request.form.get(anahtar) else 'false'
            SistemAyar.set(anahtar, deger, user_id=current_user.id)
        flash('Iletisim ayarlari basariyla kaydedildi.', 'success')
        return redirect(url_for('ayarlar.iletisim_ayar.index'))

    ayarlar = {
        'genel': SistemAyar.query.filter_by(kategori='genel').order_by(SistemAyar.id.asc()).all(),
        'akademik': SistemAyar.query.filter_by(kategori='akademik').order_by(SistemAyar.id.asc()).all(),
        'muhasebe': SistemAyar.query.filter_by(kategori='muhasebe').order_by(SistemAyar.id.asc()).all(),
        'iletisim': SistemAyar.query.filter_by(kategori='iletisim').order_by(SistemAyar.id.asc()).all(),
        'guvenlik': SistemAyar.query.filter_by(kategori='guvenlik').order_by(SistemAyar.id.asc()).all(),
    }

    return render_template('ayarlar/index.html',
                           ayarlar=ayarlar,
                           aktif_tab='iletisim')
