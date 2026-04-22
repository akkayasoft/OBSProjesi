"""Veritabani yedekleme sayfasi.

Cok-kiracili modda (MULTITENANT_ENABLED=1) yonetici/admin istedigi anda
kendi tenant'inin PostgreSQL yedegini .sql.gz olarak indirebilir.

Tek-kiracili klasik modda (SQLite/PostgreSQL) admin DB yedegini alir.

Bu sayfa yalnizca yetkili kullaniciya aciktir; pg_dump'i subprocess ile
calistirip gecici dosyaya yazar, send_file ile kullaniciya sunar, ardindan
gecici dosyayi siler.
"""
import os
import subprocess
import tempfile
from datetime import datetime
from urllib.parse import urlparse, unquote

from flask import (Blueprint, render_template, send_file, flash, redirect,
                   url_for, current_app, g, after_this_request)
from flask_login import login_required
from sqlalchemy import text

from app.utils import role_required
from app import db

bp = Blueprint('yedekleme', __name__)


# ---------------------------------------------------------------------------
# Yardimci: aktif tenant DB URL'ini cozumle
# ---------------------------------------------------------------------------

def _aktif_db_url() -> str:
    """Aktif istegin hedef veritabani URL'ini dondurur.

    - Multi-tenant acik ve g.tenant set ise: tenant'in kendi DB'si
    - Aksi halde: varsayilan SQLALCHEMY_DATABASE_URI
    """
    cfg = current_app.config
    if cfg.get('MULTITENANT_ENABLED') and getattr(g, 'tenant', None):
        tmpl = cfg.get('TENANT_DATABASE_URL_TEMPLATE') or ''
        if tmpl:
            return tmpl.format(db_name=g.tenant.db_name)
        master = cfg.get('MASTER_DATABASE_URL', '')
        if master and '/' in master:
            base, _ = master.rsplit('/', 1)
            return f'{base}/{g.tenant.db_name}'
    return cfg.get('SQLALCHEMY_DATABASE_URI', '')


def _parse_pg_url(url: str) -> dict:
    """postgresql://user:pass@host:port/dbname -> bilesenler dict."""
    p = urlparse(url)
    return {
        'user': unquote(p.username) if p.username else '',
        'password': unquote(p.password) if p.password else '',
        'host': p.hostname or 'localhost',
        'port': str(p.port or 5432),
        'dbname': (p.path or '').lstrip('/'),
    }


def _db_bilgisi() -> dict:
    """Sayfa icin gorsel DB bilgisi (tip / ad / boyut / tarih)."""
    url = _aktif_db_url()
    info = {'url': url, 'tip': None, 'adi': None, 'boyut_mb': None,
            'degistirilme': None, 'destek': False}

    if not url:
        return info

    if url.startswith('sqlite:///'):
        path = url.replace('sqlite:///', '')
        info['tip'] = 'SQLite'
        info['adi'] = os.path.basename(path)
        info['destek'] = True
        if os.path.exists(path):
            st = os.stat(path)
            info['boyut_mb'] = round(st.st_size / (1024 * 1024), 2)
            info['degistirilme'] = datetime.fromtimestamp(st.st_mtime) \
                .strftime('%d.%m.%Y %H:%M:%S')
            info['_yol'] = path
        return info

    if url.startswith('postgresql'):
        parts = _parse_pg_url(url)
        info['tip'] = 'PostgreSQL'
        info['adi'] = parts['dbname']
        info['destek'] = True
        # Boyutu veritabaninin kendisinden sor (aktif tenant baglantisindan)
        try:
            with db.engine.connect() as conn:
                boyut = conn.execute(
                    text('SELECT pg_database_size(current_database())')
                ).scalar()
                if boyut is not None:
                    info['boyut_mb'] = round(boyut / (1024 * 1024), 2)
        except Exception:
            info['boyut_mb'] = None
        info['degistirilme'] = datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        return info

    return info


# ---------------------------------------------------------------------------
# Route'lar
# ---------------------------------------------------------------------------

@bp.route('/yedekleme')
@login_required
@role_required('admin', 'yonetici')
def index():
    db_info = _db_bilgisi()
    return render_template('ayarlar/yedekleme.html', db_info=db_info)


@bp.route('/yedekleme/indir', methods=['POST'])
@login_required
@role_required('admin', 'yonetici')
def indir():
    url = _aktif_db_url()
    if not url:
        flash('Aktif veritabani URL\'i bulunamadi.', 'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))

    # --- SQLite: dosyayi dogrudan gonder ---
    if url.startswith('sqlite:///'):
        path = url.replace('sqlite:///', '')
        if not os.path.exists(path):
            flash('Veritabani dosyasi bulunamadi.', 'danger')
            return redirect(url_for('ayarlar.yedekleme.index'))
        tarih = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            path,
            as_attachment=True,
            download_name=f'{os.path.basename(path)}_{tarih}.db'
        )

    # --- PostgreSQL: pg_dump -> gzip -> send_file (gecici dosya) ---
    if not url.startswith('postgresql'):
        flash('Desteklenmeyen veritabani tipi.', 'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))

    parts = _parse_pg_url(url)
    if not parts['dbname']:
        flash('Veritabani adi cozumlenemedi.', 'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))

    # Gecici cikti dosyasi (otomatik silinmez; after_this_request ile silinir)
    fd, tmp_path = tempfile.mkstemp(prefix='obs_yedek_', suffix='.sql.gz')
    os.close(fd)

    env = os.environ.copy()
    if parts['password']:
        env['PGPASSWORD'] = parts['password']

    # pg_dump | gzip -c > tmp_path
    # Shell pipeline yerine iki process'i birbirine bagla (daha guvenli).
    try:
        with open(tmp_path, 'wb') as out:
            pg = subprocess.Popen(
                [
                    'pg_dump',
                    '-h', parts['host'],
                    '-p', parts['port'],
                    '-U', parts['user'],
                    '--no-owner',
                    '--no-privileges',
                    '--format=plain',
                    parts['dbname'],
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            gz = subprocess.Popen(
                ['gzip', '-c'],
                stdin=pg.stdout,
                stdout=out,
                stderr=subprocess.PIPE,
            )
            # pg stdout'u gz'e gecti, pg tarafinda kapat
            if pg.stdout:
                pg.stdout.close()
            gz_err = gz.communicate()[1]
            pg_err = pg.stderr.read() if pg.stderr else b''
            pg.wait()
            gz.wait()

            if pg.returncode != 0:
                current_app.logger.error(
                    'pg_dump hata: %s', pg_err.decode('utf-8', 'replace')
                )
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                flash('Yedek alinirken pg_dump hata verdi. Sunucu gunlugune '
                      'bakin.', 'danger')
                return redirect(url_for('ayarlar.yedekleme.index'))
            if gz.returncode != 0:
                current_app.logger.error(
                    'gzip hata: %s', gz_err.decode('utf-8', 'replace')
                )
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
                flash('Yedek sikistirilirken hata olustu.', 'danger')
                return redirect(url_for('ayarlar.yedekleme.index'))
    except FileNotFoundError as e:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        current_app.logger.error('pg_dump/gzip bulunamadi: %s', e)
        flash('Sunucuda pg_dump veya gzip yuklu degil.', 'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))
    except Exception as e:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        current_app.logger.exception('Yedekleme hata: %s', e)
        flash('Yedek alinamadi: beklenmeyen hata.', 'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))

    tarih = datetime.now().strftime('%Y%m%d_%H%M%S')
    indirme_adi = f"{parts['dbname']}_{tarih}.sql.gz"

    @after_this_request
    def _temizle(response):
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        return response

    return send_file(
        tmp_path,
        as_attachment=True,
        download_name=indirme_adi,
        mimetype='application/gzip',
    )
