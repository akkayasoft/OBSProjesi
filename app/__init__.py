from flask import Flask
from config import Config
from app.extensions import db, login_manager, migrate, csrf


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Uzantıları başlat
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Modelleri import et (migration için gerekli)
    from app.models import user, muhasebe, kayit, devamsizlik, personel  # noqa: F401

    # Blueprint'leri kaydet
    from app.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import main_bp
    app.register_blueprint(main_bp)

    from app.muhasebe import muhasebe_bp
    app.register_blueprint(muhasebe_bp, url_prefix='/muhasebe')

    from app.kayit import kayit_bp
    app.register_blueprint(kayit_bp, url_prefix='/kayit')

    from app.devamsizlik import devamsizlik_bp
    app.register_blueprint(devamsizlik_bp, url_prefix='/devamsizlik')

    from app.personel import personel_bp
    app.register_blueprint(personel_bp, url_prefix='/personel')

    # Context processor - sidebar menü
    @app.context_processor
    def inject_menu():
        menu_items = [
            {
                'label': 'Ana Sayfa',
                'icon': 'bi-house-door',
                'url': '/',
                'children': []
            },
            {
                'label': 'Kayıt Yönetimi',
                'icon': 'bi-journal-check',
                'url': '/kayit/',
                'children': [
                    {'label': 'Öğrenci Listesi', 'icon': 'bi-people', 'url': '/kayit/ogrenci/'},
                    {'label': 'Yeni Kayıt', 'icon': 'bi-person-plus', 'url': '/kayit/ogrenci/yeni'},
                    {'label': 'Sınıf / Şube', 'icon': 'bi-building', 'url': '/kayit/sinif/'},
                    {'label': 'Dönemler', 'icon': 'bi-calendar-range', 'url': '/kayit/donem/'},
                ]
            },
            {
                'label': 'Muhasebe',
                'icon': 'bi-cash-stack',
                'url': '/muhasebe/',
                'children': [
                    {'label': 'Gelir / Gider', 'icon': 'bi-arrow-left-right', 'url': '/muhasebe/gelir-gider/'},
                    {'label': 'Öğrenci Ödemeleri', 'icon': 'bi-mortarboard', 'url': '/muhasebe/ogrenci-odeme/'},
                    {'label': 'Personel Ödemeleri', 'icon': 'bi-people', 'url': '/muhasebe/personel-odeme/'},
                    {'label': 'Banka Hesapları', 'icon': 'bi-bank', 'url': '/muhasebe/banka/'},
                    {'label': 'Raporlar', 'icon': 'bi-bar-chart-line', 'url': '/muhasebe/raporlar/'},
                ]
            },
            {
                'label': 'Devamsızlık',
                'icon': 'bi-check2-square',
                'url': '/devamsizlik/',
                'children': [
                    {'label': 'Yoklama Al', 'icon': 'bi-clipboard-check', 'url': '/devamsizlik/yoklama/'},
                    {'label': 'Devamsızlık Raporları', 'icon': 'bi-graph-up', 'url': '/devamsizlik/rapor/'},
                ]
            },
            {
                'label': 'Personel Yönetimi',
                'icon': 'bi-person-badge',
                'url': '/personel/',
                'children': [
                    {'label': 'Personel Listesi', 'icon': 'bi-people-fill', 'url': '/personel/personel/'},
                    {'label': 'Yeni Personel', 'icon': 'bi-person-plus-fill', 'url': '/personel/personel/yeni'},
                    {'label': 'İzin Yönetimi', 'icon': 'bi-calendar-check', 'url': '/personel/izin/'},
                    {'label': 'Raporlar', 'icon': 'bi-bar-chart-line', 'url': '/personel/rapor/'},
                ]
            }
        ]
        return dict(menu_items=menu_items)

    # Seed komutu
    @app.cli.command('seed')
    def seed_command():
        """Veritabanına test verisi ekle."""
        from datetime import date, timedelta
        from app.models.user import User
        from app.models.muhasebe import (
            GelirGiderKategorisi, BankaHesabi, Ogrenci, Personel
        )

        # Admin kullanıcı
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@obs.local',
                ad='Sistem',
                soyad='Yöneticisi',
                rol='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)

        # Muhasebeci
        if not User.query.filter_by(username='muhasebe').first():
            muhasebeci = User(
                username='muhasebe',
                email='muhasebe@obs.local',
                ad='Ahmet',
                soyad='Yılmaz',
                rol='muhasebeci'
            )
            muhasebeci.set_password('muhasebe123')
            db.session.add(muhasebeci)

        # Gelir kategorileri
        gelir_kategorileri = ['Öğrenci Aidatı', 'Kayıt Ücreti', 'Kurs Ücreti', 'Kantin Geliri', 'Diğer Gelir']
        for ad in gelir_kategorileri:
            if not GelirGiderKategorisi.query.filter_by(ad=ad, tur='gelir').first():
                db.session.add(GelirGiderKategorisi(ad=ad, tur='gelir'))

        # Gider kategorileri
        gider_kategorileri = ['Personel Maaşları', 'Kira', 'Faturalar', 'Malzeme', 'Bakım/Onarım', 'Diğer Gider']
        for ad in gider_kategorileri:
            if not GelirGiderKategorisi.query.filter_by(ad=ad, tur='gider').first():
                db.session.add(GelirGiderKategorisi(ad=ad, tur='gider'))

        # Banka hesabı
        if not BankaHesabi.query.first():
            db.session.add(BankaHesabi(
                banka_adi='Ziraat Bankası',
                hesap_adi='Okul Ana Hesap',
                iban='TR000000000000000000000001',
                bakiye=0
            ))
            db.session.add(BankaHesabi(
                banka_adi='Vakıfbank',
                hesap_adi='Okul Yardımcı Hesap',
                iban='TR000000000000000000000002',
                bakiye=0
            ))

        # Örnek öğrenciler
        ornek_ogrenciler = [
            ('1001', 'Ayşe', 'Demir', '9-A'),
            ('1002', 'Mehmet', 'Kaya', '9-B'),
            ('1003', 'Zeynep', 'Çelik', '10-A'),
            ('1004', 'Ali', 'Yıldız', '10-B'),
            ('1005', 'Fatma', 'Öztürk', '11-A'),
        ]
        for no, ad, soyad, sinif in ornek_ogrenciler:
            if not Ogrenci.query.filter_by(ogrenci_no=no).first():
                db.session.add(Ogrenci(ogrenci_no=no, ad=ad, soyad=soyad, sinif=sinif))

        # Örnek personeller
        ornek_personeller = [
            ('P001', 'Hasan', 'Aksoy', 'Matematik Öğretmeni', 25000, 'Matematik', 'tam_zamanli', '05301112233'),
            ('P002', 'Elif', 'Şahin', 'Türkçe Öğretmeni', 24000, 'Türkçe', 'tam_zamanli', '05302223344'),
            ('P003', 'Murat', 'Koç', 'Müdür', 35000, 'İdari', 'tam_zamanli', '05303334455'),
            ('P004', 'Ayşe', 'Yılmaz', 'Fen Bilgisi Öğretmeni', 24500, 'Fen Bilimleri', 'tam_zamanli', '05304445566'),
            ('P005', 'Zehra', 'Kara', 'İngilizce Öğretmeni', 23000, 'Yabancı Dil', 'yari_zamanli', '05305556677'),
        ]
        for sicil, ad, soyad, pozisyon, maas, departman, calisma_turu, telefon in ornek_personeller:
            mevcut = Personel.query.filter_by(sicil_no=sicil).first()
            if not mevcut:
                db.session.add(Personel(
                    sicil_no=sicil, ad=ad, soyad=soyad,
                    pozisyon=pozisyon, maas=maas,
                    departman=departman, calisma_turu=calisma_turu,
                    telefon=telefon,
                    ise_baslama_tarihi=date(2023, 9, 1)
                ))
            else:
                mevcut.departman = mevcut.departman or departman
                mevcut.calisma_turu = mevcut.calisma_turu or calisma_turu
                mevcut.telefon = mevcut.telefon or telefon
                mevcut.ise_baslama_tarihi = mevcut.ise_baslama_tarihi or date(2023, 9, 1)

        db.session.commit()

        # === Kayıt Yönetimi seed verisi ===
        from app.models.kayit import Sinif, Sube, KayitDonemi

        # Sınıflar
        sinif_verileri = [
            ('9. Sınıf', 9), ('10. Sınıf', 10),
            ('11. Sınıf', 11), ('12. Sınıf', 12)
        ]
        for ad, seviye in sinif_verileri:
            if not Sinif.query.filter_by(ad=ad).first():
                db.session.add(Sinif(ad=ad, seviye=seviye))
        db.session.commit()

        # Şubeler
        for sinif in Sinif.query.all():
            for sube_ad in ['A', 'B']:
                mevcut = Sube.query.filter_by(sinif_id=sinif.id, ad=sube_ad).first()
                if not mevcut:
                    db.session.add(Sube(sinif_id=sinif.id, ad=sube_ad, kontenjan=30))
        db.session.commit()

        # Dönem
        if not KayitDonemi.query.first():
            db.session.add(KayitDonemi(
                ad='2025-2026',
                baslangic_tarihi=date(2025, 9, 1),
                bitis_tarihi=date(2026, 6, 30),
                aktif=True,
                aciklama='2025-2026 Eğitim Öğretim Yılı'
            ))
            db.session.commit()

        # === Devamsızlık seed verisi ===
        from app.models.devamsizlik import Devamsizlik

        # Get admin user for olusturan
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user and Devamsizlik.query.count() == 0:
            # Get students and classes for seed data
            ogrenciler = Ogrenci.query.all()
            subeler = Sube.query.all()

            if ogrenciler and subeler:
                # Create attendance records for the past 10 days
                today = date.today()
                durumlar = ['devamsiz', 'gec', 'izinli', 'raporlu']

                for i in range(1, 11):  # Last 10 days
                    tarih = today - timedelta(days=i)

                    # Assign students to classes and create records
                    for idx, ogrenci in enumerate(ogrenciler):
                        sube = subeler[idx % len(subeler)]

                        # Create records for 4 lessons per day
                        for ders_saati in range(1, 5):
                            # Randomly assign status (70% present, 30% absent/late/etc)
                            import random
                            durum = durumlar[random.randint(0, 3)] if random.random() > 0.7 else 'hazir'

                            # Check if record already exists
                            mevcut = Devamsizlik.query.filter_by(
                                ogrenci_id=ogrenci.id,
                                sube_id=sube.id,
                                tarih=tarih,
                                ders_saati=ders_saati
                            ).first()

                            if not mevcut:
                                db.session.add(Devamsizlik(
                                    ogrenci_id=ogrenci.id,
                                    sube_id=sube.id,
                                    tarih=tarih,
                                    ders_saati=ders_saati,
                                    durum=durum,
                                    olusturan_id=admin_user.id
                                ))
                db.session.commit()

        # === Personel İzin seed verisi ===
        from app.models.personel import PersonelIzin

        if admin_user and PersonelIzin.query.count() == 0:
            personel_listesi = Personel.query.all()
            if personel_listesi:
                izin_verileri = [
                    (personel_listesi[0].id, 'yillik', date(2026, 1, 6), date(2026, 1, 10), 5, 'onaylandi', 'Yılbaşı tatili'),
                    (personel_listesi[1].id, 'saglik', date(2026, 2, 15), date(2026, 2, 17), 3, 'onaylandi', 'Sağlık raporu'),
                    (personel_listesi[0].id, 'mazeret', date(2026, 3, 20), date(2026, 3, 21), 2, 'beklemede', 'Aile ziyareti'),
                    (personel_listesi[2].id, 'idari', date(2026, 3, 10), date(2026, 3, 10), 1, 'onaylandi', 'Toplantı'),
                    (personel_listesi[3].id if len(personel_listesi) > 3 else personel_listesi[0].id, 'yillik', date(2026, 4, 1), date(2026, 4, 5), 5, 'beklemede', 'Bahar tatili'),
                ]
                for p_id, turu, bas, bit, gun, durum, aciklama in izin_verileri:
                    db.session.add(PersonelIzin(
                        personel_id=p_id,
                        izin_turu=turu,
                        baslangic_tarihi=bas,
                        bitis_tarihi=bit,
                        gun_sayisi=gun,
                        durum=durum,
                        aciklama=aciklama,
                        olusturan_id=admin_user.id,
                        onaylayan_id=admin_user.id if durum == 'onaylandi' else None,
                    ))
                db.session.commit()

        print('Seed verisi başarıyla eklendi!')

    return app
