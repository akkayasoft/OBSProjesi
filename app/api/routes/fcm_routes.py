"""Mobil API — FCM cihaz token kaydi."""
from flask import request, g

from app.extensions import db
from app.api.auth import api_auth, api_basarili, api_hata


def register(bp):

    @bp.route('/fcm-token', methods=['POST'])
    @api_auth
    def fcm_token_kaydet():
        """Mobil cihazin FCM token'ini kaydet/guncelle (push bildirim).

        Ayni token zaten varsa kullaniciya yeniden baglanir
        (cihaz el degistirmis olabilir).
        """
        veri = request.get_json(silent=True) or {}
        token = (veri.get('token') or '').strip()
        platform = (veri.get('platform') or 'android').strip()
        if not token:
            return api_hata('Token gerekli.', 400)

        from app.models.bildirim import CihazTokeni
        mevcut = CihazTokeni.query.filter_by(token=token).first()
        if mevcut is None:
            db.session.add(CihazTokeni(
                kullanici_id=g.api_user.id,
                token=token,
                platform=platform,
                aktif=True,
            ))
        else:
            mevcut.kullanici_id = g.api_user.id
            mevcut.platform = platform
            mevcut.aktif = True
        db.session.commit()
        return api_basarili({'kayitli': True})
