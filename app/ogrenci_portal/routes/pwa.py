"""PWA (Progressive Web App) endpoints — manifest, service worker, offline
sayfa ve Web Push (VAPID) abonelik uc noktalari.

Service worker'i /portal/ scope'unda calistirmak icin dosyayi /portal/ altindan
servis ediyoruz. Boylece SW'in scope'u /portal/* olur (sadece ogrenci/veli
portali PWA kapsaminda).
"""
import os
from datetime import datetime

from flask import (Blueprint, current_app, jsonify, make_response,
                   render_template, request, send_from_directory)
from flask_login import current_user, login_required

from app.extensions import csrf, db
from app.models.bildirim import PushAbonelik


bp = Blueprint('pwa', __name__)


def _static_pwa_dir() -> str:
    return os.path.join(current_app.root_path, 'static', 'pwa')


@bp.route('/manifest.webmanifest')
def manifest():
    response = make_response(send_from_directory(_static_pwa_dir(),
                                                 'manifest.webmanifest'))
    response.headers['Content-Type'] = 'application/manifest+json'
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response


@bp.route('/service-worker.js')
def service_worker():
    response = make_response(send_from_directory(_static_pwa_dir(),
                                                 'service-worker.js'))
    response.headers['Content-Type'] = 'application/javascript'
    # SW kendi basina revalidate etsin; tarayici cache'ini sifirliyoruz ki
    # yeni surumler zamaninda yayinlansin.
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    # Scope'u genisletmek isteseydik: response.headers['Service-Worker-Allowed'] = '/'
    return response


@bp.route('/offline')
def offline():
    """Cevrimdisi fallback sayfasi. SW bu sayfayi precache eder."""
    return render_template('ogrenci_portal/offline.html')


# === Web Push (VAPID) endpoint'leri ===========================================

@bp.route('/push/vapid-key')
def push_vapid_key():
    """Tarayicinin PushManager.subscribe() icin kullanacagi public anahtar."""
    pub = current_app.config.get('VAPID_PUBLIC_KEY', '')
    return jsonify({'key': pub, 'enabled': bool(pub)})


@bp.route('/push/abone-ol', methods=['POST'])
@login_required
@csrf.exempt
def push_abone_ol():
    """Tarayicidan gelen subscription bilgisini DB'ye kaydet."""
    data = request.get_json(silent=True) or {}
    endpoint = (data.get('endpoint') or '').strip()
    keys = data.get('keys') or {}
    p256dh = (keys.get('p256dh') or '').strip()
    auth = (keys.get('auth') or '').strip()
    if not endpoint or not p256dh or not auth:
        return jsonify({'ok': False, 'msg': 'Eksik abonelik bilgisi'}), 400

    user_agent = (request.headers.get('User-Agent') or '')[:500]
    mevcut = PushAbonelik.query.filter_by(endpoint=endpoint).first()
    if mevcut:
        mevcut.kullanici_id = current_user.id
        mevcut.p256dh = p256dh
        mevcut.auth = auth
        mevcut.user_agent = user_agent
        mevcut.aktif = True
        mevcut.son_kullanim = datetime.utcnow()
    else:
        db.session.add(PushAbonelik(
            kullanici_id=current_user.id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
            user_agent=user_agent,
            aktif=True,
        ))
    db.session.commit()
    return jsonify({'ok': True})


@bp.route('/push/abone-cik', methods=['POST'])
@login_required
@csrf.exempt
def push_abone_cik():
    """Bir endpoint icin aboneligi sil."""
    data = request.get_json(silent=True) or {}
    endpoint = (data.get('endpoint') or '').strip()
    if not endpoint:
        return jsonify({'ok': False, 'msg': 'endpoint gerekli'}), 400
    silinen = PushAbonelik.query.filter_by(
        endpoint=endpoint, kullanici_id=current_user.id
    ).delete()
    db.session.commit()
    return jsonify({'ok': True, 'silinen': silinen})


@bp.route('/push/test', methods=['POST'])
@login_required
@csrf.exempt
def push_test():
    """Giris yapmis kullanicinin kendi cihazlarina test bildirimi gonderir."""
    from app.utils.push import push_gonder_user
    basarili = push_gonder_user(
        current_user.id,
        title='OBS Bildirim Testi',
        body=f'Merhaba {current_user.ad}, bildirimleriniz calisiyor!',
        url='/portal/',
    )
    return jsonify({'ok': True, 'gonderilen': basarili})
