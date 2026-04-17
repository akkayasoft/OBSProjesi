"""PWA (Progressive Web App) endpoints — manifest, service worker, offline sayfa.

Service worker'i /portal/ scope'unda calistirmak icin dosyayi /portal/ altindan
servis ediyoruz. Boylece SW'in scope'u /portal/* olur (sadece ogrenci/veli
portali PWA kapsaminda).
"""
import os
from flask import Blueprint, send_from_directory, render_template, current_app, make_response


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
