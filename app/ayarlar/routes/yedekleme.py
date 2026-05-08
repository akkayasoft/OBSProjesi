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


# ---------------------------------------------------------------------------
# Geri yukleme (RESTORE) — destructive operation, sadece admin/yonetici
# ---------------------------------------------------------------------------

ONAY_METNI = 'GERI YUKLE'
MAX_YEDEK_BOYUT_MB = 200


def _admin_psql_url():
    """CREATE/DROP DATABASE icin admin baglantisi."""
    cfg = current_app.config
    return cfg.get('TENANT_ADMIN_DATABASE_URL') or \
        cfg.get('MASTER_DATABASE_URL')


def _pg_drop_create(db_name: str):
    """Tenant DB'sini DROP + CREATE et. Aktif baglantilari terminate eder."""
    import psycopg2
    admin_url = _admin_psql_url()
    if not admin_url:
        raise RuntimeError('Admin DB URL bulunamadi.')
    parts = _parse_pg_url(admin_url)
    conn = psycopg2.connect(
        host=parts['host'], port=parts['port'],
        user=parts['user'], password=parts['password'],
        dbname=parts['dbname'] or 'postgres',
    )
    conn.autocommit = True
    cur = conn.cursor()
    try:
        # Aktif tum baglantilari terminate et
        cur.execute("""
            SELECT pg_terminate_backend(pid)
              FROM pg_stat_activity
             WHERE datname = %s AND pid <> pg_backend_pid()
        """, (db_name,))
        cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        cur.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        cur.close()
        conn.close()


def _pg_dump_to_file(db_name: str, parts: dict, out_path: str) -> bool:
    """pg_dump | gzip -> out_path. True=ok, False=hata."""
    env = os.environ.copy()
    if parts.get('password'):
        env['PGPASSWORD'] = parts['password']
    try:
        with open(out_path, 'wb') as out:
            pg = subprocess.Popen(
                ['pg_dump', '-h', parts['host'], '-p', parts['port'],
                 '-U', parts['user'], '--no-owner', '--no-privileges',
                 '--format=plain', db_name],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
            )
            gz = subprocess.Popen(
                ['gzip', '-c'], stdin=pg.stdout, stdout=out,
                stderr=subprocess.PIPE,
            )
            if pg.stdout:
                pg.stdout.close()
            gz.communicate()
            pg.wait()
            gz.wait()
            return pg.returncode == 0 and gz.returncode == 0
    except Exception:
        return False


@bp.route('/yedekleme/geri-yukle', methods=['POST'])
@login_required
@role_required('admin', 'yonetici')
def geri_yukle():
    """Aktif tenant DB'sine yedek geri yukle.

    Akis:
      1) Onay metni dogrulamasi ('GERI YUKLE')
      2) Yuklenmis dosya kontrolu (.sql veya .sql.gz, < 200 MB)
      3) Otomatik 'oncesi' yedek (hata olursa elle restore icin)
      4) Tenant DB'sini DROP + CREATE
      5) Yedeği psql ile yukle
      6) Kullaniciyi cikisa zorla
    """
    onay = (request.form.get('onay') or '').strip().upper()
    if onay != ONAY_METNI:
        flash(f'Onay metni hatalı. Geri yüklemek için "{ONAY_METNI}" '
              f'yazmanız gerekir.', 'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))

    yuklenen = request.files.get('yedek_dosyasi')
    if not yuklenen or not yuklenen.filename:
        flash('Yedek dosyası seçilmedi.', 'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))

    fname = yuklenen.filename
    if not (fname.endswith('.sql') or fname.endswith('.sql.gz')):
        flash('Yedek dosyası .sql veya .sql.gz formatında olmalı.', 'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))

    url = _aktif_db_url()
    if not url or not url.startswith('postgresql'):
        flash('Bu işlem yalnızca PostgreSQL veritabanlarında çalışır.',
              'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))
    parts = _parse_pg_url(url)
    db_name = parts['dbname']
    if not db_name:
        flash('Veritabanı adı çözümlenemedi.', 'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))

    # 1) Yuklenen dosyayi gecici dizine kaydet
    suffix = '.sql.gz' if fname.endswith('.sql.gz') else '.sql'
    fd, yedek_yolu = tempfile.mkstemp(prefix='obs_restore_', suffix=suffix)
    os.close(fd)
    try:
        yuklenen.save(yedek_yolu)
        boyut_mb = os.path.getsize(yedek_yolu) / (1024 * 1024)
        if boyut_mb > MAX_YEDEK_BOYUT_MB:
            os.unlink(yedek_yolu)
            flash(f'Yedek dosyası çok büyük ({boyut_mb:.1f} MB). '
                  f'Üst sınır {MAX_YEDEK_BOYUT_MB} MB.', 'danger')
            return redirect(url_for('ayarlar.yedekleme.index'))

        # .gz ise unzip et
        if suffix == '.sql.gz':
            sql_yolu = yedek_yolu[:-3]  # .gz uzantisini kaldir
            try:
                with subprocess.Popen(
                    ['gunzip', '-c', yedek_yolu], stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ) as gz:
                    out, err = gz.communicate()
                    if gz.returncode != 0:
                        raise RuntimeError(
                            f'gunzip hata: {err.decode("utf-8", "replace")}'
                        )
                with open(sql_yolu, 'wb') as f:
                    f.write(out)
            except Exception as e:
                current_app.logger.exception('gunzip hata: %s', e)
                os.unlink(yedek_yolu)
                flash('Yedek dosyası açılamadı (gunzip hatası).', 'danger')
                return redirect(url_for('ayarlar.yedekleme.index'))
            try:
                os.unlink(yedek_yolu)
            except Exception:
                pass
        else:
            sql_yolu = yedek_yolu

        # 2) Format dogrulamasi: ilk 4KB'da PostgreSQL dump signature ara
        try:
            with open(sql_yolu, 'rb') as f:
                bas = f.read(4096).decode('utf-8', errors='replace')
            if 'PostgreSQL database dump' not in bas and \
                    'CREATE TABLE' not in bas.upper() and \
                    'COPY ' not in bas.upper():
                os.unlink(sql_yolu)
                flash('Dosya geçerli bir PostgreSQL yedeği gibi görünmüyor. '
                      'pg_dump çıktısı olmalıdır.', 'danger')
                return redirect(url_for('ayarlar.yedekleme.index'))
        except Exception:
            pass  # validation best-effort, gec

        # 3) ONCESI yedek (rollback icin) — opsiyonel ama tavsiyye
        # /var/backups/obs_restore'i dene, yazilamazsa /tmp'a dus
        oncesi_path = None
        for kok_dizin in ('/var/backups/obs_restore', '/tmp'):
            try:
                os.makedirs(kok_dizin, exist_ok=True)
                tarih = datetime.now().strftime('%Y%m%d_%H%M%S')
                yol = os.path.join(
                    kok_dizin, f'oncesi_{db_name}_{tarih}.sql.gz'
                )
                ok = _pg_dump_to_file(db_name, parts, yol)
                if ok:
                    oncesi_path = yol
                    break
            except Exception as e:
                current_app.logger.warning(
                    'Oncesi yedek %s yoluna alinamadi: %s', kok_dizin, e
                )
                continue

        # 4) DROP + CREATE
        try:
            _pg_drop_create(db_name)
        except Exception as e:
            current_app.logger.exception('DROP/CREATE basarisiz: %s', e)
            try:
                os.unlink(sql_yolu)
            except Exception:
                pass
            flash(f'Veritabanı yeniden oluşturulamadı: {e}', 'danger')
            return redirect(url_for('ayarlar.yedekleme.index'))

        # 5) psql -f sql_yolu ile uygula
        env = os.environ.copy()
        if parts.get('password'):
            env['PGPASSWORD'] = parts['password']
        try:
            sonuc = subprocess.run(
                ['psql', '-h', parts['host'], '-p', parts['port'],
                 '-U', parts['user'], '-d', db_name,
                 '-v', 'ON_ERROR_STOP=1', '-q', '-f', sql_yolu],
                env=env, capture_output=True, text=True, timeout=600,
            )
            if sonuc.returncode != 0:
                current_app.logger.error(
                    'psql restore hata (rc=%s): %s',
                    sonuc.returncode,
                    (sonuc.stderr or sonuc.stdout)[:2000],
                )
                msg = ('Yedek geri yüklenirken hata oluştu. '
                       'Veritabanı boş olabilir; yöneticiye başvurun.')
                if oncesi_path:
                    msg += (f' Önceki durumu sunucudan geri yüklemek için '
                            f'şu dosya kullanılabilir: {oncesi_path}')
                flash(msg, 'danger')
                return redirect(url_for('ayarlar.yedekleme.index'))
        except subprocess.TimeoutExpired:
            flash('Geri yükleme zaman aşımına uğradı (>10 dk).', 'danger')
            return redirect(url_for('ayarlar.yedekleme.index'))
        except Exception as e:
            current_app.logger.exception('psql restore hata: %s', e)
            flash(f'Geri yükleme başarısız: {e}', 'danger')
            return redirect(url_for('ayarlar.yedekleme.index'))
        finally:
            try:
                os.unlink(sql_yolu)
            except Exception:
                pass

    except Exception as e:
        current_app.logger.exception('Geri yukleme akisi hatasi: %s', e)
        flash(f'Beklenmeyen hata: {e}', 'danger')
        return redirect(url_for('ayarlar.yedekleme.index'))

    # 6) Cikisa zorla — session bozulmus olabilir
    from flask_login import logout_user
    logout_user()
    flash('Yedek başarıyla geri yüklendi. Lütfen tekrar giriş yapın.',
          'success')
    return redirect(url_for('auth.giris'))
