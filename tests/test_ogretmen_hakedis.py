"""Ogretmen Hak Edis modulu testleri.

- Gunluk ders saati toplami x saatlik ucret = hak edis
- 'Odendi' isaretlenince otomatik PersonelOdemeKaydi + gider kaydi olusur
- Geri alinca gider kaydi temizlenir
"""
from datetime import date
from decimal import Decimal


def _ogretmen(db_session, saatlik_ucret='350'):
    from app.models.muhasebe import Personel
    p = Personel(
        sicil_no='OG001', ad='Salih', soyad='Hoca',
        pozisyon='Öğretmen', departman='Matematik',
        saatlik_ucret=Decimal(saatlik_ucret), aktif=True,
    )
    db_session.add(p)
    db_session.commit()
    return p


def _ders_saati_ekle(db_session, personel, gun_saat, yil=2026, ay=1):
    """gun_saat: {1: 4, 5: 3, ...}"""
    from app.models.muhasebe import OgretmenDersSaati
    for gun, saat in gun_saat.items():
        db_session.add(OgretmenDersSaati(
            personel_id=personel.id, tarih=date(yil, ay, gun),
            saat=Decimal(str(saat)),
        ))
    db_session.commit()


def test_aylik_toplam_saat_dogru_hesaplanir(app, db_session, admin_user):
    from app.ogretmen_hakedis import _personel_ay_toplami
    p = _ogretmen(db_session)
    _ders_saati_ekle(db_session, p, {1: 4, 5: 3, 8: 4, 15: 8})
    with app.test_request_context():
        toplam = _personel_ay_toplami(p.id, 2026, 1)
    assert toplam == Decimal('19'), f'19 saat beklendi, {toplam} bulundu'


def test_maliyet_sayfasi_acilir_ve_hak_edis_gosterir(
    app, db_session, authed_client,
):
    p = _ogretmen(db_session, saatlik_ucret='350')
    _ders_saati_ekle(db_session, p, {1: 10, 2: 10, 3: 10, 4: 10})  # 40 saat
    resp = authed_client.get('/ogretmen-hakedis/maliyet?ay=2026-01')
    assert resp.status_code == 200
    # 40 saat x 350 = 14000
    assert b'14000' in resp.data.replace(b'.', b'').replace(b',', b'')


def test_odendi_isaretlenince_gider_kaydi_olusur(
    app, db_session, authed_client, banka_hesap,
):
    from app.models.muhasebe import PersonelOdemeKaydi, GelirGiderKaydi
    p = _ogretmen(db_session, saatlik_ucret='300')
    _ders_saati_ekle(db_session, p, {1: 5, 2: 5})  # 10 saat -> 3000 TL

    resp = authed_client.post(
        f'/ogretmen-hakedis/ode/{p.id}',
        data={'ay': '2026-01', 'odeme_turu': 'havale', 'banka_hesap_id': '0'},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    odeme = PersonelOdemeKaydi.query.filter_by(personel_id=p.id).first()
    assert odeme is not None, 'Hak edis odeme kaydi olusmadi'
    assert odeme.tutar == Decimal('3000.0')
    assert odeme.gelir_gider_kayit_id is not None, \
        'Odeme yapildi ama gider kaydi olusmadi'

    gider = GelirGiderKaydi.query.get(odeme.gelir_gider_kayit_id)
    assert gider.tur == 'gider'
    assert gider.tutar == Decimal('3000.0')


def test_ayni_ay_iki_kez_odenemez(
    app, db_session, authed_client, banka_hesap,
):
    from app.models.muhasebe import PersonelOdemeKaydi
    p = _ogretmen(db_session, saatlik_ucret='300')
    _ders_saati_ekle(db_session, p, {1: 5, 2: 5})

    for _ in range(2):
        authed_client.post(
            f'/ogretmen-hakedis/ode/{p.id}',
            data={'ay': '2026-01', 'odeme_turu': 'havale',
                  'banka_hesap_id': '0'},
            follow_redirects=True,
        )
    sayi = PersonelOdemeKaydi.query.filter_by(personel_id=p.id).count()
    assert sayi == 1, f'Mukerrer odeme olustu: {sayi} kayit'


def test_ode_geri_al_gider_kaydini_temizler(
    app, db_session, authed_client, banka_hesap,
):
    from app.models.muhasebe import PersonelOdemeKaydi, GelirGiderKaydi
    p = _ogretmen(db_session, saatlik_ucret='300')
    _ders_saati_ekle(db_session, p, {1: 5, 2: 5})
    authed_client.post(
        f'/ogretmen-hakedis/ode/{p.id}',
        data={'ay': '2026-01', 'odeme_turu': 'havale', 'banka_hesap_id': '0'},
        follow_redirects=True,
    )
    odeme = PersonelOdemeKaydi.query.filter_by(personel_id=p.id).first()
    gider_id = odeme.gelir_gider_kayit_id

    authed_client.post(
        f'/ogretmen-hakedis/ode-geri-al/{odeme.id}',
        follow_redirects=True,
    )
    assert PersonelOdemeKaydi.query.get(odeme.id) is None
    assert GelirGiderKaydi.query.get(gider_id) is None, \
        'Geri alindi ama gider kaydi duruyor'


def test_ders_saati_girisi_grid_kaydeder(
    app, db_session, authed_client,
):
    from app.models.muhasebe import OgretmenDersSaati
    p = _ogretmen(db_session)
    resp = authed_client.post(
        '/ogretmen-hakedis/giris?ay=2026-01',
        data={'csrf_token': 'x', f's_{p.id}_1': '4', f's_{p.id}_5': '3'},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    kayitlar = OgretmenDersSaati.query.filter_by(personel_id=p.id).all()
    assert len(kayitlar) == 2
    assert sum(Decimal(str(k.saat)) for k in kayitlar) == Decimal('7')
