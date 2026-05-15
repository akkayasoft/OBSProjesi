"""Mobil API — Devamsizlik (ogrenci/veli)."""
from flask import g, request
from sqlalchemy import extract

from app.api.auth import api_auth, api_basarili, api_hata
from app.api.yardimci import hedef_ogrenci, ogrenci_ozet


def _kayit_ozet(d):
    return {
        'id': d.id,
        'tarih': d.tarih.isoformat() if d.tarih else None,
        'ders_saati': d.ders_saati,
        'durum': d.durum,            # devamsiz / gec / izinli / raporlu
        'aciklama': d.aciklama,
    }


def register(bp):

    @bp.route('/devamsizlik', methods=['GET'])
    @api_auth
    def devamsizlik():
        """Ogrencinin devamsizlik kayitlari + ozet.

        Opsiyonel ?ay=YYYY-MM ile aya gore filtre.
        """
        ogrenci = hedef_ogrenci(g.api_user)
        if ogrenci is None:
            return api_hata('Bu hesaba bagli ogrenci bulunamadi.', 404)

        from app.models.devamsizlik import Devamsizlik
        q = Devamsizlik.query.filter_by(ogrenci_id=ogrenci.id)

        ay = request.args.get('ay')
        if ay:
            try:
                yil, aynum = ay.split('-')
                q = q.filter(
                    extract('year', Devamsizlik.tarih) == int(yil),
                    extract('month', Devamsizlik.tarih) == int(aynum),
                )
            except (ValueError, AttributeError):
                pass

        kayitlar = q.order_by(
            Devamsizlik.tarih.desc(),
            Devamsizlik.ders_saati.asc(),
        ).all()

        ozet = {'devamsiz': 0, 'gec': 0, 'izinli': 0,
                'raporlu': 0, 'toplam': len(kayitlar)}
        for d in kayitlar:
            if d.durum in ozet:
                ozet[d.durum] += 1

        return api_basarili(
            [_kayit_ozet(d) for d in kayitlar],
            ogrenci=ogrenci_ozet(ogrenci),
            ozet=ozet,
        )
