"""Mobil API — Deneme sinavi sonuclari (ogrenci/veli)."""
from flask import g

from app.api.auth import api_auth, api_basarili, api_hata
from app.api.yardimci import hedef_ogrenci, ogrenci_ozet


def _katilim_ozet(k):
    """Liste gorunumu — bir deneme katiliminin ozeti."""
    s = k.sinav
    return {
        'katilim_id': k.id,
        'sinav': {
            'id': s.id,
            'ad': s.ad,
            'tip': getattr(s, 'tip_str', s.sinav_tipi),
            'tarih': s.tarih.isoformat() if s.tarih else None,
        },
        'toplam_dogru': k.toplam_dogru,
        'toplam_yanlis': k.toplam_yanlis,
        'toplam_bos': k.toplam_bos,
        'toplam_net': k.toplam_net,
        'toplam_puan': k.toplam_puan,
    }


def register(bp):

    @bp.route('/denemeler', methods=['GET'])
    @api_auth
    def denemeler():
        """Ogrencinin katildigi deneme sinavlari (en yeni once)."""
        ogrenci = hedef_ogrenci(g.api_user)
        if ogrenci is None:
            return api_hata('Bu hesaba bagli ogrenci bulunamadi.', 404)

        from app.models.deneme_sinavi import DenemeKatilim, DenemeSinavi
        katilimlar = (DenemeKatilim.query
                      .join(DenemeSinavi,
                            DenemeKatilim.deneme_sinavi_id == DenemeSinavi.id)
                      .filter(DenemeKatilim.ogrenci_id == ogrenci.id,
                              DenemeKatilim.katildi.is_(True))
                      .order_by(DenemeSinavi.tarih.desc())
                      .all())
        return api_basarili(
            [_katilim_ozet(k) for k in katilimlar],
            ogrenci=ogrenci_ozet(ogrenci),
        )

    @bp.route('/denemeler/<int:katilim_id>', methods=['GET'])
    @api_auth
    def deneme_detay(katilim_id):
        """Bir deneme katiliminin ders bazli detayi + siralama."""
        ogrenci = hedef_ogrenci(g.api_user)
        if ogrenci is None:
            return api_hata('Bu hesaba bagli ogrenci bulunamadi.', 404)

        from app.models.deneme_sinavi import DenemeKatilim
        k = DenemeKatilim.query.filter_by(id=katilim_id).first()
        if k is None or k.ogrenci_id != ogrenci.id:
            return api_hata('Deneme kaydi bulunamadi.', 404)

        s = k.sinav

        # Ders bazli sonuclar
        ders_sonuclari = []
        for ds in k.ders_sonuclari.all():
            ders_sonuclari.append({
                'ders': ds.ders.ders_adi if ds.ders else '—',
                'dogru': ds.dogru,
                'yanlis': ds.yanlis,
                'bos': ds.bos,
                'net': ds.net,
            })

        # Siralama — toplam_net'e gore
        net = k.toplam_net or 0
        ust_sayi = DenemeKatilim.query.filter(
            DenemeKatilim.deneme_sinavi_id == s.id,
            DenemeKatilim.katildi.is_(True),
            DenemeKatilim.toplam_net > net,
        ).count()
        toplam_katilimci = DenemeKatilim.query.filter_by(
            deneme_sinavi_id=s.id, katildi=True).count()

        return api_basarili({
            'katilim_id': k.id,
            'sinav': {
                'id': s.id,
                'ad': s.ad,
                'tip': getattr(s, 'tip_str', s.sinav_tipi),
                'tarih': s.tarih.isoformat() if s.tarih else None,
                'ortalama_net': s.ortalama_net,
            },
            'sonuc': {
                'toplam_dogru': k.toplam_dogru,
                'toplam_yanlis': k.toplam_yanlis,
                'toplam_bos': k.toplam_bos,
                'toplam_net': k.toplam_net,
                'toplam_puan': k.toplam_puan,
            },
            'siralama': ust_sayi + 1,
            'toplam_katilimci': toplam_katilimci,
            'ders_sonuclari': ders_sonuclari,
        }, ogrenci=ogrenci_ozet(ogrenci))
