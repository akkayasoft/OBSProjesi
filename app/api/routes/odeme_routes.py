"""Mobil API — Odeme / borc durumu (ogrenci/veli)."""
from flask import g

from app.api.auth import api_auth, api_basarili, api_hata
from app.api.yardimci import hedef_ogrenci, ogrenci_ozet


def _taksit_ozet(t):
    return {
        'taksit_no': t.taksit_no,
        'tutar': float(t.tutar),
        'odenen': float(t.odenen_tutar or 0),
        'kalan': t.kalan,
        'vade_tarihi': t.vade_tarihi.isoformat() if t.vade_tarihi else None,
        'odeme_tarihi': (t.odeme_tarihi.isoformat()
                         if t.odeme_tarihi else None),
        'durum': t.durum,            # beklemede/odendi/gecikti/kismi_odendi
        'gecikti_mi': t.gecikti_mi,
    }


def _plan_ozet(p):
    taksitler = sorted(p.taksitler, key=lambda t: t.taksit_no)
    return {
        'id': p.id,
        'donem': p.donem,
        'net_tutar': p.net_tutar,
        'odenen': p.odenen_toplam,
        'kalan': p.kalan_borc,
        'taksit_sayisi': p.taksit_sayisi,
        'durum': p.durum,
        'taksitler': [_taksit_ozet(t) for t in taksitler],
    }


def register(bp):

    @bp.route('/odemeler', methods=['GET'])
    @api_auth
    def odemeler():
        """Ogrencinin odeme planlari, taksitleri ve borc ozeti."""
        ogrenci = hedef_ogrenci(g.api_user)
        if ogrenci is None:
            return api_hata('Bu hesaba bagli ogrenci bulunamadi.', 404)

        from app.models.muhasebe import OdemePlani
        planlar = (OdemePlani.query
                   .filter(OdemePlani.ogrenci_id == ogrenci.id,
                           OdemePlani.durum != 'iptal')
                   .order_by(OdemePlani.olusturma_tarihi.desc())
                   .all())

        plan_ozetleri = [_plan_ozet(p) for p in planlar]
        toplam = sum(p['net_tutar'] for p in plan_ozetleri)
        odenen = sum(p['odenen'] for p in plan_ozetleri)
        kalan = sum(p['kalan'] for p in plan_ozetleri)
        geciken = sum(
            1 for p in plan_ozetleri for t in p['taksitler']
            if t['gecikti_mi']
        )

        return api_basarili(
            {
                'planlar': plan_ozetleri,
                'ozet': {
                    'toplam_borc': round(toplam, 2),
                    'odenen': round(odenen, 2),
                    'kalan': round(kalan, 2),
                    'geciken_taksit': geciken,
                },
            },
            ogrenci=ogrenci_ozet(ogrenci),
        )
