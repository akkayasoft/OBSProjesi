from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.ayarlar import SistemAyar
from app.extensions import db

bp = Blueprint('akademik', __name__)


@bp.route('/akademik', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def index():
    if request.method == 'POST':
        anahtarlar = ['gecme_notu', 'not_sistemi', 'max_devamsizlik_gun',
                       'sinav_agirlik_yazili', 'sinav_agirlik_sozlu', 'sinav_agirlik_performans']
        for anahtar in anahtarlar:
            deger = request.form.get(anahtar, '')
            SistemAyar.set(anahtar, deger, user_id=current_user.id)
        flash('Akademik ayarlar basariyla kaydedildi.', 'success')
        return redirect(url_for('ayarlar.akademik.index'))

    ayarlar = {
        'genel': SistemAyar.query.filter_by(kategori='genel').order_by(SistemAyar.id.asc()).all(),
        'akademik': SistemAyar.query.filter_by(kategori='akademik').order_by(SistemAyar.id.asc()).all(),
        'muhasebe': SistemAyar.query.filter_by(kategori='muhasebe').order_by(SistemAyar.id.asc()).all(),
        'iletisim': SistemAyar.query.filter_by(kategori='iletisim').order_by(SistemAyar.id.asc()).all(),
        'guvenlik': SistemAyar.query.filter_by(kategori='guvenlik').order_by(SistemAyar.id.asc()).all(),
    }

    return render_template('ayarlar/index.html',
                           ayarlar=ayarlar,
                           aktif_tab='akademik')
