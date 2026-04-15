from datetime import datetime, date
from app.extensions import db
from app.models.muhasebe import Odeme, BankaHesabi, BankaHareketi


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
