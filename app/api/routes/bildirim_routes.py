"""Mobil API — Bildirimler ve Duyurular."""
from datetime import datetime

from flask import g, request

from app.extensions import db
from app.api.auth import api_auth, api_basarili, api_hata

# Kullanici rol -> Duyuru.hedef_kitle eslesmesi
_HEDEF_HARITASI = {
    'ogrenci': 'ogrenciler',
    'veli': 'veliler',
    'ogretmen': 'ogretmenler',
    'muhasebeci': 'personel',
    'admin': 'personel',
    'yonetici': 'personel',
}


def _bildirim_ozet(b):
    return {
        'id': b.id,
        'baslik': b.baslik,
        'mesaj': b.mesaj,
        'tur': b.tur,
        'kategori': b.kategori,
        'link': b.link,
        'okundu': b.okundu,
        'tarih': b.created_at.isoformat() if b.created_at else None,
    }


def _duyuru_ozet(d, okundu):
    return {
        'id': d.id,
        'baslik': d.baslik,
        'icerik': d.icerik,
        'kategori': d.kategori,
        'oncelik': d.oncelik,
        'sabitlenmis': d.sabitlenmis,
        'okundu': okundu,
        'tarih': (d.yayinlanma_tarihi.isoformat()
                  if d.yayinlanma_tarihi else None),
    }


def register(bp):

    # ---------------- Bildirimler ----------------
    @bp.route('/bildirimler', methods=['GET'])
    @api_auth
    def bildirimler():
        """Kullanicinin bildirimleri (en yeni once, son 50)."""
        from app.models.bildirim import Bildirim
        q = (Bildirim.query
             .filter_by(kullanici_id=g.api_user.id)
             .order_by(Bildirim.created_at.desc())
             .limit(50).all())
        okunmamis = Bildirim.okunmamis_sayisi(g.api_user.id)
        return api_basarili(
            [_bildirim_ozet(b) for b in q],
            okunmamis=okunmamis,
        )

    @bp.route('/bildirimler/<int:bildirim_id>/okundu', methods=['POST'])
    @api_auth
    def bildirim_okundu(bildirim_id):
        """Tek bildirimi okundu isaretle."""
        from app.models.bildirim import Bildirim
        b = Bildirim.query.filter_by(
            id=bildirim_id, kullanici_id=g.api_user.id).first()
        if b is None:
            return api_hata('Bildirim bulunamadi.', 404)
        if not b.okundu:
            b.okundu = True
            b.okunma_tarihi = datetime.utcnow()
            db.session.commit()
        return api_basarili({'id': b.id, 'okundu': True})

    @bp.route('/bildirimler/tumunu-okundu', methods=['POST'])
    @api_auth
    def bildirimler_tumunu_okundu():
        """Tum bildirimleri okundu isaretle."""
        from app.models.bildirim import Bildirim
        adet = (Bildirim.query
                .filter_by(kullanici_id=g.api_user.id, okundu=False)
                .update({'okundu': True,
                         'okunma_tarihi': datetime.utcnow()}))
        db.session.commit()
        return api_basarili({'okundu_isaretlenen': adet})

    # ---------------- Duyurular ----------------
    @bp.route('/duyurular', methods=['GET'])
    @api_auth
    def duyurular():
        """Kullanicinin rolune uygun aktif duyurular."""
        from app.models.duyurular import Duyuru
        hedef = _HEDEF_HARITASI.get(g.api_user.rol)
        hedefler = ['tumu']
        if hedef:
            hedefler.append(hedef)

        q = (Duyuru.query
             .filter(Duyuru.aktif.is_(True),
                     Duyuru.hedef_kitle.in_(hedefler))
             .order_by(Duyuru.sabitlenmis.desc(),
                       Duyuru.yayinlanma_tarihi.desc())
             .limit(50).all())
        # Suresi dolmuslari ele
        aktif_duyurular = [d for d in q if not d.suresi_doldu]
        return api_basarili([
            _duyuru_ozet(d, d.kullanici_okudu_mu(g.api_user.id))
            for d in aktif_duyurular
        ])

    @bp.route('/duyurular/<int:duyuru_id>', methods=['GET'])
    @api_auth
    def duyuru_detay(duyuru_id):
        """Tek duyuru detayi — goruntulenince okundu kaydi olusur."""
        from app.models.duyurular import Duyuru, DuyuruOkunma
        d = Duyuru.query.filter_by(id=duyuru_id, aktif=True).first()
        if d is None:
            return api_hata('Duyuru bulunamadi.', 404)
        if not d.kullanici_okudu_mu(g.api_user.id):
            db.session.add(DuyuruOkunma(
                duyuru_id=d.id, kullanici_id=g.api_user.id))
            d.okunma_sayisi = (d.okunma_sayisi or 0) + 1
            db.session.commit()
        return api_basarili(_duyuru_ozet(d, True))
