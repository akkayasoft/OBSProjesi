"""Mobil uygulama push bildirim — FCM (Firebase Cloud Messaging).

Bir Bildirim olusturuldugunda (hangi kod yolundan olursa olsun)
kullanicinin kayitli mobil cihazlarina push gonderir.

Firebase service account JSON gerektirir; ortam degiskeni
FIREBASE_SERVICE_ACCOUNT ile yolu verilir. Dosya yoksa modul
sessizce devre disi kalir (no-op) — uygulamayi etkilemez.
"""
import os
import threading

from sqlalchemy import event
from sqlalchemy.orm import Session

_kilit = threading.Lock()
_baslatildi = False
_etkin = False
_olaylar_kayitli = False


def _firebase_baslat() -> bool:
    """firebase-admin'i tek seferlik baslat. Servis hesabi yoksa False."""
    global _baslatildi, _etkin
    if _baslatildi:
        return _etkin
    with _kilit:
        if _baslatildi:
            return _etkin
        _baslatildi = True
        yol = os.environ.get('FIREBASE_SERVICE_ACCOUNT')
        if not yol or not os.path.isfile(yol):
            print('[fcm] FIREBASE_SERVICE_ACCOUNT tanimli degil — '
                  'push bildirim devre disi.')
            return False
        try:
            import firebase_admin
            from firebase_admin import credentials
            if not firebase_admin._apps:
                firebase_admin.initialize_app(
                    credentials.Certificate(yol))
            _etkin = True
            print('[fcm] Firebase push bildirim etkin.')
        except Exception as e:
            print(f'[fcm] Firebase baslatilamadi: {e}')
        return _etkin


def _gonderileri_isle(gonderiler):
    """Arka plan thread'i — (token, baslik, mesaj) listesini FCM'e gonder."""
    try:
        from firebase_admin import messaging
    except Exception:
        return
    for token, baslik, mesaj in gonderiler:
        try:
            messaging.send(messaging.Message(
                token=token,
                notification=messaging.Notification(
                    title=baslik, body=mesaj),
                android=messaging.AndroidConfig(
                    priority='high',
                    # Yuksek oncelikli kanal -> ust banner + ses
                    notification=messaging.AndroidNotification(
                        channel_id='obs_bildirim',
                        sound='default',
                        default_sound=True,
                    ),
                ),
            ))
        except Exception:
            # Gecersiz/suresi dolmus token — sessizce atla
            pass


def fcm_olaylarini_kaydet():
    """Bildirim insert + commit olaylarini dinle.

    Her yeni Bildirim icin commit sonrasi, ilgili kullanicinin mobil
    cihazlarina push gonderir. Boylece devamsizlik, odeme, deneme vb.
    tum bildirim tipleri otomatik push tetikler.
    """
    global _olaylar_kayitli
    if _olaylar_kayitli:
        return
    _olaylar_kayitli = True
    from app.models.bildirim import Bildirim

    @event.listens_for(Bildirim, 'after_insert')
    def _bildirim_eklendi(mapper, connection, target):
        sess = Session.object_session(target)
        if sess is None:
            return
        kova = sess.info.setdefault('_fcm_bekleyen', [])
        kova.append((target.kullanici_id, target.baslik, target.mesaj))

    @event.listens_for(Session, 'after_commit')
    def _commit_sonrasi(sess):
        kova = sess.info.pop('_fcm_bekleyen', None)
        if not kova or not _firebase_baslat():
            return
        try:
            from app.models.bildirim import CihazTokeni
            gonderiler = []
            for kullanici_id, baslik, mesaj in kova:
                tokenlar = CihazTokeni.query.filter_by(
                    kullanici_id=kullanici_id, aktif=True).all()
                for c in tokenlar:
                    gonderiler.append((c.token, baslik, mesaj))
            if gonderiler:
                threading.Thread(
                    target=_gonderileri_isle,
                    args=(gonderiler,),
                    daemon=True,
                ).start()
        except Exception as e:
            print(f'[fcm] commit sonrasi push hazirlama hatasi: {e}')
