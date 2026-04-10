import os
from flask import Blueprint, render_template, send_file, flash, redirect, url_for, current_app
from flask_login import login_required
from app.utils import role_required

bp = Blueprint('yedekleme', __name__)


@bp.route('/yedekleme')
@login_required
@role_required('admin')
def index():
    db_path = _get_db_path()
    db_info = {}
    if db_path and os.path.exists(db_path):
        stat = os.stat(db_path)
        db_info['dosya_adi'] = os.path.basename(db_path)
        db_info['boyut_mb'] = round(stat.st_size / (1024 * 1024), 2)
        db_info['boyut_kb'] = round(stat.st_size / 1024, 2)
        from datetime import datetime
        db_info['degistirilme'] = datetime.fromtimestamp(stat.st_mtime).strftime('%d.%m.%Y %H:%M:%S')
        db_info['yol'] = db_path
    else:
        db_info = None

    return render_template('ayarlar/yedekleme.html', db_info=db_info)


@bp.route('/yedekleme/indir', methods=['POST'])
@login_required
@role_required('admin')
def indir():
    db_path = _get_db_path()
    if db_path and os.path.exists(db_path):
        return send_file(
            db_path,
            as_attachment=True,
            download_name='obs_yedek.db'
        )
    flash('Veritabani dosyasi bulunamadi.', 'danger')
    return redirect(url_for('ayarlar.yedekleme.index'))


def _get_db_path():
    """Veritabani dosya yolunu dondurur."""
    db_uri = current_app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('sqlite:///'):
        return db_uri.replace('sqlite:///', '')
    return None
