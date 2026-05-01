from datetime import datetime, date
from app.extensions import db
from app.models.muhasebe import (Odeme, BankaHesabi, BankaHareketi,
                                  GelirGiderKategorisi, GelirGiderKaydi)


OGRENCI_AIDAT_KATEGORI_ADI = 'Öğrenci Aidatı'


def _aidat_kategorisi_getir():
    """Ogrenci odemesi icin gelir kategorisini getir; yoksa olustur."""
    kat = GelirGiderKategorisi.query.filter_by(
        ad=OGRENCI_AIDAT_KATEGORI_ADI, tur='gelir',
    ).first()
    if kat is None:
        kat = GelirGiderKategorisi(
            ad=OGRENCI_AIDAT_KATEGORI_ADI, tur='gelir', aktif=True,
        )
        db.session.add(kat)
        db.session.flush()
    return kat


def odeme_icin_gelir_kaydi_olustur(odeme):
    """Ogrenci odemesi icin otomatik 'Ogrenci Aidati' gelir kaydi olustur
    ve odeme.gelir_gider_kayit_id'i set et.

    Idempotent: zaten link varsa hicbir sey yapmaz.
    """
    if odeme.gelir_gider_kayit_id:
        return None
    kat = _aidat_kategorisi_getir()
    taksit = odeme.taksit
    ogrenci = taksit.odeme_plani.ogrenci if taksit and taksit.odeme_plani else None
    if ogrenci is None:
        return None  # baglanmamis bir odeme, atla
    aciklama = (
        f'{ogrenci.tam_ad} — '
        f'{taksit.taksit_no}. taksit ödemesi '
        f'(Makbuz: {odeme.makbuz_no})'
    )
    kayit = GelirGiderKaydi(
        tur='gelir',
        kategori_id=kat.id,
        tutar=odeme.tutar,
        aciklama=aciklama,
        tarih=odeme.tarih.date() if hasattr(odeme.tarih, 'date') else odeme.tarih,
        belge_no=odeme.makbuz_no,
        banka_hesap_id=odeme.banka_hesap_id,
        olusturan_id=odeme.olusturan_id,
    )
    db.session.add(kayit)
    db.session.flush()
    odeme.gelir_gider_kayit_id = kayit.id
    return kayit


def odeme_gelir_kaydini_temizle(odeme):
    """Odemeye bagli gelir kaydi varsa sil ve linki kopar.
    Muhasebe ekraninda elle silinmis olabilir — guvenli."""
    if not odeme.gelir_gider_kayit_id:
        return
    kayit = GelirGiderKaydi.query.filter_by(
        id=odeme.gelir_gider_kayit_id,
    ).first()
    if kayit:
        db.session.delete(kayit)
    odeme.gelir_gider_kayit_id = None


def makbuz_no_uret():
    """MKB-YYYYMMDD-XXXX formatında makbuz numarası üretir."""
    bugun = datetime.now().strftime('%Y%m%d')
    prefix = f'MKB-{bugun}-'

    son_makbuz = Odeme.query.filter(
        Odeme.makbuz_no.like(f'{prefix}%')
    ).order_by(Odeme.makbuz_no.desc()).first()

    if son_makbuz:
        son_no = int(son_makbuz.makbuz_no.split('-')[-1])
        yeni_no = son_no + 1
    else:
        yeni_no = 1

    return f'{prefix}{yeni_no:04d}'


def banka_hareketi_olustur(hesap_id, tur, tutar, aciklama='', karsi_hesap_id=None):
    """Banka hareketi oluşturur ve bakiyeyi günceller."""
    hesap = BankaHesabi.query.get(hesap_id)
    if not hesap:
        return None

    hareket = BankaHareketi(
        banka_hesap_id=hesap_id,
        tur=tur,
        tutar=tutar,
        karsi_hesap_id=karsi_hesap_id,
        aciklama=aciklama,
        tarih=datetime.utcnow()
    )

    if tur == 'giris':
        hesap.bakiye = float(hesap.bakiye) + float(tutar)
    elif tur == 'cikis':
        hesap.bakiye = float(hesap.bakiye) - float(tutar)

    db.session.add(hareket)
    return hareket


def geciken_taksitleri_guncelle():
    """Vadesi geçmiş taksitlerin durumunu günceller."""
    from app.models.muhasebe import Taksit, OdemePlani

    geciken = Taksit.query.join(OdemePlani).filter(
        Taksit.durum.in_(['beklemede', 'kismi_odendi']),
        Taksit.vade_tarihi < date.today(),
        OdemePlani.durum == 'aktif'
    ).all()

    for taksit in geciken:
        if float(taksit.odenen_tutar) > 0:
            taksit.durum = 'kismi_odendi'
        else:
            taksit.durum = 'gecikti'

    db.session.commit()
