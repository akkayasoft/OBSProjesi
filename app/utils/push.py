"""Web Push (VAPID) yardimci fonksiyonlari.

Kullanim:
    from app.utils.push import push_gonder_user, push_gonder_kullanicilar
    push_gonder_user(user_id, 'Yeni duyuru', 'Veli toplantisi yarin 18:00',
                     url='/portal/duyurular/')

Backend'den her push gonderimi icin pywebpush ile istek gonderilir. Gecersiz
abonelikler (404/410) otomatik olarak veritabanindan silinir.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Iterable

from flask import current_app
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from app.extensions import db
from app.models.bildirim import PushAbonelik


logger = logging.getLogger(__name__)

# pywebpush, vapid_private_key parametresine raw string verildiginde
# Vapid.from_string() kullanir (raw base64url ister). Biz PEM tutuyoruz,
# o yuzden Vapid objesini bir kez olusturup ornek olarak cache'liyoruz.
_vapid_cache: dict = {}


def _vapid_objesi() -> Vapid | None:
    """PEM'den Vapid objesi olustur (cache'li). Yoksa None."""
    priv = (current_app.config.get('VAPID_PRIVATE_KEY') or '').strip()
    if not priv:
        return None
    cached = _vapid_cache.get('key'), _vapid_cache.get('obj')
    if cached[0] == priv and cached[1] is not None:
        return cached[1]
    try:
        obj = Vapid.from_pem(priv.encode('utf-8'))
    except Exception as e:  # noqa: BLE001
        logger.warning('VAPID PEM parse edilemedi: %s', e)
        return None
    _vapid_cache['key'] = priv
    _vapid_cache['obj'] = obj
    return obj


def _vapid_ayarlari() -> tuple[Vapid, dict] | None:
    """Yapilandirmadan VAPID objesi + claims cek. Eksikse None dondur."""
    vapid = _vapid_objesi()
    if vapid is None:
        return None
    email = current_app.config.get('VAPID_CLAIM_EMAIL') or 'mailto:admin@obs.local'
    return vapid, {'sub': email}


def push_gonder_abonelik(abonelik: PushAbonelik, payload: dict) -> bool:
    """Tek aboneliğe push gonder. Gecersizse abonelik silinir.

    Return: True = basarili, False = gonderilemedi/silindi.
    """
    ayar = _vapid_ayarlari()
    if not ayar:
        logger.debug('VAPID yapilandirilmadi — push atlandi')
        return False
    vapid_obj, claims = ayar
    try:
        webpush(
            subscription_info=abonelik.subscription_info(),
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=vapid_obj,
            vapid_claims=claims,
            ttl=60 * 60 * 24,  # 24 saat
        )
        abonelik.son_kullanim = datetime.utcnow()
        db.session.commit()
        return True
    except WebPushException as e:
        status = getattr(getattr(e, 'response', None), 'status_code', None)
        # 404 = endpoint yok, 410 = kalıcı silinmiş
        if status in (404, 410):
            logger.info('Gecersiz push abonelik silindi: %s', abonelik.id)
            db.session.delete(abonelik)
            db.session.commit()
        else:
            logger.warning('Push gonderim hatasi (%s): %s', status, e)
        return False
    except Exception as e:  # noqa: BLE001
        logger.warning('Push gonderim genel hata: %s', e)
        return False


def push_gonder_user(kullanici_id: int, title: str, body: str,
                     url: str | None = None, icon: str | None = None,
                     tag: str | None = None) -> int:
    """Belirli bir kullanicinin tum aktif cihazlarina push gonder.

    Return: basarili gonderim sayisi.
    """
    aboneler = PushAbonelik.query.filter_by(
        kullanici_id=kullanici_id, aktif=True
    ).all()
    if not aboneler:
        return 0
    payload = {
        'title': title,
        'body': body,
        'url': url or '/portal/',
        'icon': icon or '/static/pwa/icons/icon-192.png',
        'badge': '/static/pwa/icons/icon-192.png',
        'tag': tag or f'obs-{kullanici_id}',
    }
    basarili = 0
    for a in aboneler:
        if push_gonder_abonelik(a, payload):
            basarili += 1
    return basarili


def push_gonder_kullanicilar(kullanici_ids: Iterable[int], title: str,
                             body: str, url: str | None = None,
                             icon: str | None = None,
                             tag: str | None = None) -> int:
    """Bir kullanici listesine toplu push gonder.

    Return: toplam basarili gonderim sayisi.
    """
    toplam = 0
    for kid in kullanici_ids:
        toplam += push_gonder_user(kid, title, body, url=url, icon=icon, tag=tag)
    return toplam
