"""Mobil uygulama API'si — JSON + JWT.

Bagimsiz Flutter mobil uygulamasi bu API uzerinden OBS verisine
erisir. Web portalindan tamamen ayri, /api/v1 prefix'i altinda
calisir; web tarafina dokunmaz.

Yanit formati:
  Basarili : {"basarili": true, "veri": {...}}
  Hata     : {"basarili": false, "hata": "mesaj"}
"""
from flask import Blueprint, jsonify

api_bp = Blueprint('api', __name__)


@api_bp.errorhandler(404)
def _api_404(e):
    return jsonify({'basarili': False, 'hata': 'Kaynak bulunamadi.'}), 404


@api_bp.errorhandler(405)
def _api_405(e):
    return jsonify({'basarili': False,
                    'hata': 'Bu metoda izin verilmiyor.'}), 405


@api_bp.errorhandler(500)
def _api_500(e):
    return jsonify({'basarili': False, 'hata': 'Sunucu hatasi.'}), 500


from app.api.routes import register_routes  # noqa: E402
register_routes(api_bp)
