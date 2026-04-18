"""Deneme sinavi sonuclari icin otomatik bildirim (in-app + Web Push).

Sonuc kaydedildiginde hem ogrenciye hem de velilerine bildirim gonderilir.
Helper idempotent degildir — her cagirildiginda yeni Bildirim kaydi uretir.
Ayni katilim icin tekrar cagrilmamasi icin cagiran taraf (routes/cevap.py)
yalnizca yeni/guncellenen katilimlari set halinde toplayip bir kere cagirir.
"""
from __future__ import annotations

import logging
from typing import Iterable

from flask import url_for

from app.extensions import db
from app.models.bildirim import Bildirim
from app.models.kayit import VeliBilgisi
from app.models.deneme_sinavi import DenemeKatilim
from app.utils.push import push_gonder_user


logger = logging.getLogger(__name__)


def _hedef_kullanici_idleri(katilim: DenemeKatilim) -> list[int]:
    """Bildirim alacak kullanici id'leri: ogrenci + tum veliler."""
    ids: list[int] = []
    ogrenci = katilim.ogrenci
    if ogrenci is None:
        return ids
    if ogrenci.user_id:
        ids.append(ogrenci.user_id)
    veliler = (VeliBilgisi.query
               .filter(VeliBilgisi.ogrenci_id == ogrenci.id,
                       VeliBilgisi.user_id.isnot(None))
               .all())
    for v in veliler:
        if v.user_id and v.user_id not in ids:
            ids.append(v.user_id)
    return ids


def _mesaj_olustur(katilim: DenemeKatilim) -> tuple[str, str]:
    """(baslik, mesaj) ciftini olustur."""
    sinav = katilim.sinav
    ad = sinav.ad if sinav else 'Deneme Sinavi'
    ogr_ad = katilim.ogrenci.tam_ad if katilim.ogrenci else 'Ogrenci'
    net = katilim.toplam_net
    puan = katilim.toplam_puan
    baslik = f'{ad} sonucu yayinlandi'
    parcalar = [f'{ogr_ad} icin sonuclar girildi.']
    if net is not None:
        parcalar.append(f'Toplam net: {net:.2f}')
    if puan is not None:
        parcalar.append(f'Puan: {puan:.2f}')
    mesaj = ' '.join(parcalar)
    return baslik, mesaj


def bildirim_gonder_katilim(katilim: DenemeKatilim) -> int:
    """Tek bir DenemeKatilim icin ogrenci + velilere bildirim gonder.

    Return: olusturulan Bildirim kaydi sayisi (push gonderimleri disinda).
    Push gonderimi sirasinda olusabilecek hatalar yutulur (loglanir).
    """
    hedefler = _hedef_kullanici_idleri(katilim)
    if not hedefler:
        return 0

    baslik, mesaj = _mesaj_olustur(katilim)
    try:
        link = url_for('ogrenci_portal.deneme_sinavi_portal.detay',
                       katilim_id=katilim.id)
    except Exception:  # noqa: BLE001
        link = f'/portal/deneme-sinavi/{katilim.id}'

    # In-app bildirim (commit'i cagiran fonksiyon yapsin — burada session
    # bosaltilmasin). Bildirim.olustur() commit ediyor; toplu ekleyelim.
    olusan = 0
    for kid in hedefler:
        db.session.add(Bildirim(
            kullanici_id=kid,
            baslik=baslik,
            mesaj=mesaj,
            tur='basari',
            kategori='sinav',
            link=link,
        ))
        olusan += 1

    # Web Push (abonelikler ayri commit yapiyor, ama cagirana problem olmaz)
    for kid in hedefler:
        try:
            push_gonder_user(kid, baslik, mesaj, url=link, tag=f'deneme-{katilim.id}')
        except Exception as e:  # noqa: BLE001
            logger.warning('Push gonderilemedi (user=%s): %s', kid, e)

    return olusan


def bildirim_gonder_katilimlar(katilimlar: Iterable[DenemeKatilim]) -> int:
    """Birden fazla katilim icin toplu bildirim (ayni commit icinde)."""
    toplam = 0
    for k in katilimlar:
        toplam += bildirim_gonder_katilim(k)
    return toplam
