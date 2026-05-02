"""Pytest fixture'lari — tum testler bu modulu otomatik gorur.

Test stratejisi:
- SQLite in-memory DB (hizli, izole, her test yeni baslangic)
- MULTITENANT_ENABLED=False (single-tenant moda dus, master DB gerekmez)
- CSRF kapali (test client'in CSRF token uretmesini bekleme)
- Flask-Login session set ile authentikasyon mock
"""
import os
import pytest
from datetime import date, datetime
from decimal import Decimal


# Test environment — config.py'tan once set edilmeli
os.environ['MULTITENANT_ENABLED'] = '0'
os.environ['MASTER_DATABASE_URL'] = ''
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'test-secret-key-not-for-prod'
os.environ['WTF_CSRF_ENABLED'] = 'False'
os.environ['TESTING'] = '1'


@pytest.fixture(scope='function')
def app():
    """Her test icin temiz Flask app + temiz DB."""
    from app import create_app
    from app.extensions import db
    from config import Config

    class TestConfig(Config):
        TESTING = True
        WTF_CSRF_ENABLED = False
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        MASTER_DATABASE_URL = ''
        MULTITENANT_ENABLED = False
        SECRET_KEY = 'test-secret-key'

    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def db_session(app):
    """db.session shortcut'i."""
    from app.extensions import db
    return db.session


@pytest.fixture
def admin_user(app, db_session):
    """admin rollu test kullanicisi."""
    from app.models.user import User
    u = User(username='test_admin', email='admin@test.local',
            ad='Test', soyad='Admin', rol='admin', aktif=True)
    u.set_password('test12345')
    db_session.add(u)
    db_session.commit()
    return u


@pytest.fixture
def banka_hesap(app, db_session):
    """Test banka hesabi."""
    from app.models.muhasebe import BankaHesabi
    h = BankaHesabi(
        banka_adi='Test Bankasi', hesap_adi='Ana Hesap',
        iban='TR000000000000000000000099',
        bakiye=Decimal('0'), aktif=True,
    )
    db_session.add(h)
    db_session.commit()
    return h


@pytest.fixture
def authed_client(app, admin_user):
    """Flask-Login session'i set edilmis test client.

    Tarayici gibi davranir; @login_required route'lar acilir.
    """
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin_user.id)
        sess['_fresh'] = True
    return client


@pytest.fixture
def ogrenci_with_plan(app, db_session, admin_user):
    """Bir ogrenci + odeme plani + 3 taksit."""
    from app.models.muhasebe import Ogrenci, OdemePlani, Taksit

    ogr = Ogrenci(
        ogrenci_no='T001', ad='Ali', soyad='Test',
        tc_kimlik='10000000000', cinsiyet='erkek',
        sinif='9-A', aktif=True,
    )
    db_session.add(ogr)
    db_session.commit()

    plan = OdemePlani(
        ogrenci_id=ogr.id, donem='2025-2026',
        toplam_tutar=Decimal('9000'),
        indirim_tutar=Decimal('0'),
        taksit_sayisi=3,
        durum='aktif',
    )
    db_session.add(plan)
    db_session.commit()

    for i, vade in enumerate([date(2026, 5, 1), date(2026, 6, 1),
                               date(2026, 7, 1)], start=1):
        db_session.add(Taksit(
            odeme_plani_id=plan.id, taksit_no=i,
            tutar=Decimal('3000'), vade_tarihi=vade,
            odenen_tutar=Decimal('0'), durum='beklemede',
        ))
    db_session.commit()

    return ogr, plan
