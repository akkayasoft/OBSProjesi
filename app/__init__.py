from flask import Flask, render_template, request
from config import Config
from app.extensions import db, login_manager, migrate, csrf
from app.tenancy import init_tenancy


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Multi-tenant altyapisi — master DB, CLI, middleware (flag aciksa).
    # db.init_app'ten ONCE tanitiriz ki before_request middleware'lerinde
    # sira dogru olsun (tenant cozumlemesi kullanici yukleyicisinden once).
    init_tenancy(app)

    # Uzantıları başlat
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Modelleri import et (migration için gerekli)
    from app.models import user, muhasebe, kayit, devamsizlik, personel, ders_dagitimi, not_defteri, duyurular, rehberlik, saglik, iletisim, online_sinav, kulupler, kurum, ayarlar, bildirim, denetim, belge, deneme_sinavi  # noqa: F401

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

    from app.ders_dagitimi import ders_dagitimi_bp
    app.register_blueprint(ders_dagitimi_bp, url_prefix='/ders-dagitimi')

    from app.not_defteri import not_defteri_bp
    app.register_blueprint(not_defteri_bp, url_prefix='/not-defteri')

    from app.duyurular import duyurular_bp
    app.register_blueprint(duyurular_bp, url_prefix='/duyurular')

    from app.rehberlik import rehberlik_bp
    app.register_blueprint(rehberlik_bp, url_prefix='/rehberlik')

    from app.saglik import saglik_bp
    app.register_blueprint(saglik_bp, url_prefix='/saglik')

    from app.iletisim import iletisim_bp
    app.register_blueprint(iletisim_bp, url_prefix='/iletisim')

    from app.online_sinav import online_sinav_bp
    app.register_blueprint(online_sinav_bp, url_prefix='/online-sinav')

    from app.kulupler import kulupler_bp
    app.register_blueprint(kulupler_bp, url_prefix='/kulupler')

    from app.kullanici import kullanici_bp
    app.register_blueprint(kullanici_bp, url_prefix='/kullanici')

    from app.kurum import kurum_bp
    app.register_blueprint(kurum_bp, url_prefix='/kurum')

    from app.ayarlar import ayarlar_bp
    app.register_blueprint(ayarlar_bp, url_prefix='/ayarlar')

    from app.ogretmen_portal import ogretmen_portal_bp
    app.register_blueprint(ogretmen_portal_bp, url_prefix='/ogretmen')

    from app.ogrenci_portal import ogrenci_portal_bp
    app.register_blueprint(ogrenci_portal_bp, url_prefix='/portal')

    from app.bildirim import bildirim_bp
    app.register_blueprint(bildirim_bp, url_prefix='/bildirim')

    from app.odev_takip import odev_takip_bp
    app.register_blueprint(odev_takip_bp, url_prefix='/odev')

    from app.davranis import davranis_bp
    app.register_blueprint(davranis_bp, url_prefix='/davranis')

    from app.karne import karne_bp
    app.register_blueprint(karne_bp, url_prefix='/karne')

    from app.etut import etut_bp
    app.register_blueprint(etut_bp, url_prefix='/etut')

    from app.sinav_oturum import sinav_oturum_bp
    app.register_blueprint(sinav_oturum_bp, url_prefix='/sinav-oturum')

    from app.ortak_sinav import ortak_sinav_bp
    app.register_blueprint(ortak_sinav_bp, url_prefix='/ortak-sinav')

    from app.deneme_sinavi import deneme_sinavi_bp
    app.register_blueprint(deneme_sinavi_bp, url_prefix='/deneme-sinavi')

    from app.anket import anket_bp
    app.register_blueprint(anket_bp, url_prefix='/anket')

    from app.servis import servis_bp
    app.register_blueprint(servis_bp, url_prefix='/servis')

    from app.kantin import kantin_bp
    app.register_blueprint(kantin_bp, url_prefix='/kantin')

    from app.kutuphane import kutuphane_bp
    app.register_blueprint(kutuphane_bp, url_prefix='/kutuphane')

    from app.envanter import envanter_bp
    app.register_blueprint(envanter_bp, url_prefix='/envanter')

    from app.yurt import yurt_bp
    app.register_blueprint(yurt_bp, url_prefix='/yurt')

    from app.raporlama import raporlama_bp
    app.register_blueprint(raporlama_bp, url_prefix='/raporlama')

    from app.denetim import denetim_bp
    app.register_blueprint(denetim_bp, url_prefix='/denetim')

    from app.belge import belge_bp
    app.register_blueprint(belge_bp, url_prefix='/belge')

    from app.ders_programi import ders_programi_bp
    app.register_blueprint(ders_programi_bp, url_prefix='/ders-programi')

    # 403 hata sayfası
    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    # Context processor - bildirim sayısı
    @app.context_processor
    def inject_bildirim_sayisi():
        from flask_login import current_user
        if current_user.is_authenticated:
            from app.models.bildirim import Bildirim
            return dict(okunmamis_bildirim=Bildirim.okunmamis_sayisi(current_user.id))
        return dict(okunmamis_bildirim=0)

    # Footer icin yil + surum + statik dosya cache-busting
    # Surum, custom.css'in mtime'inden hesaplaniyor — dosya degistikce
    # query string degisir, browser yeni dosyayi indirir.
    import os as _os
    _static_root = _os.path.join(_os.path.dirname(__file__), 'static')

    def _asset_versiyonu():
        try:
            css_path = _os.path.join(_static_root, 'css', 'custom.css')
            js_path = _os.path.join(_static_root, 'js', 'app.js')
            mtime = max(_os.path.getmtime(css_path), _os.path.getmtime(js_path))
            return str(int(mtime))
        except OSError:
            return '1'

    @app.context_processor
    def inject_footer():
        from datetime import date
        return dict(
            now_yil=date.today().year,
            obs_surum=app.config.get('OBS_SURUM', '1.0'),
            asset_v=_asset_versiyonu(),
        )

    # Context processor - sidebar menü
    @app.context_processor
    def inject_menu():
        from flask_login import current_user
        from app.models.ayarlar import RolModulIzin

        all_menu_items = [
            {'label': 'Ana Sayfa', 'icon': 'bi-house-door', 'url': '/', 'modul_key': None, 'children': []},
            {'label': 'Öğretmen Portalı', 'icon': 'bi-person-workspace', 'url': '/ogretmen/', 'modul_key': 'ogretmen_portal', 'children': [
                {'label': 'Ders Programım', 'icon': 'bi-calendar-week', 'url': '/ogretmen/program/'},
                {'label': 'Sınıflarım', 'icon': 'bi-people', 'url': '/ogretmen/siniflarim/'},
                {'label': 'Notlarım', 'icon': 'bi-journal-check', 'url': '/ogretmen/notlar/'},
                {'label': 'Yoklama', 'icon': 'bi-clipboard-check', 'url': '/ogretmen/yoklama/'},
                {'label': 'Mesajlarım', 'icon': 'bi-envelope', 'url': '/ogretmen/mesajlar/'},
            ]},
            {'label': 'Öğrenci Portalı', 'icon': 'bi-mortarboard', 'url': '/portal/', 'modul_key': 'ogrenci_portal', 'children': [
                {'label': 'Notlarım', 'icon': 'bi-journal-check', 'url': '/portal/notlar/'},
                {'label': 'Devamsızlık', 'icon': 'bi-calendar-x', 'url': '/portal/devamsizlik/'},
                {'label': 'Ders Programı', 'icon': 'bi-calendar-week', 'url': '/portal/program/'},
                {'label': 'Sınavlar', 'icon': 'bi-pencil-square', 'url': '/portal/sinavlar/'},
                {'label': 'Duyurular', 'icon': 'bi-megaphone', 'url': '/portal/duyurular/'},
                {'label': 'Ödeme Durumu', 'icon': 'bi-cash-stack', 'url': '/portal/muhasebe/'},
            ]},
            {'label': 'Kullanıcı Yönetimi', 'icon': 'bi-shield-lock', 'url': '/kullanici/', 'modul_key': 'kullanici', 'children': [
                {'label': 'Kullanıcı Listesi', 'icon': 'bi-people', 'url': '/kullanici/liste'},
                {'label': 'Yeni Kullanıcı', 'icon': 'bi-person-plus', 'url': '/kullanici/yeni'},
            ]},
            {'label': 'Kurum Yönetimi', 'icon': 'bi-building', 'url': '/kurum/', 'modul_key': 'kurum', 'children': [
                {'label': 'Kurum Bilgileri', 'icon': 'bi-info-circle', 'url': '/kurum/bilgi'},
                {'label': 'Öğretim Yılları', 'icon': 'bi-calendar-range', 'url': '/kurum/ogretim-yili/'},
                {'label': 'Tatiller', 'icon': 'bi-calendar-x', 'url': '/kurum/tatil/'},
                {'label': 'Derslikler', 'icon': 'bi-door-open', 'url': '/kurum/derslik/'},
            ]},
            {'label': 'Kayıt Yönetimi', 'icon': 'bi-journal-check', 'url': '/kayit/', 'modul_key': 'kayit', 'children': [
                {'label': 'Öğrenci Listesi', 'icon': 'bi-people', 'url': '/kayit/ogrenci/'},
                {'label': 'Yeni Kayıt', 'icon': 'bi-person-plus', 'url': '/kayit/ogrenci/yeni'},
                {'label': 'Veliler', 'icon': 'bi-people-fill', 'url': '/kayit/veli/',
                 'roller': ['admin', 'yonetici']},
                {'label': 'Sınıf / Şube', 'icon': 'bi-building', 'url': '/kayit/sinif/',
                 'roller': ['admin', 'yonetici']},
                {'label': 'Dönemler', 'icon': 'bi-calendar-range', 'url': '/kayit/donem/',
                 'roller': ['admin', 'yonetici']},
            ]},
            {'label': 'Muhasebe', 'icon': 'bi-cash-stack', 'url': '/muhasebe/', 'modul_key': 'muhasebe', 'children': [
                {'label': 'Gelir / Gider', 'icon': 'bi-arrow-left-right', 'url': '/muhasebe/gelir-gider/'},
                {'label': 'Öğrenci Ödemeleri', 'icon': 'bi-mortarboard', 'url': '/muhasebe/ogrenci-odeme/'},
                {'label': 'Tahsilat Hareketliliği', 'icon': 'bi-receipt', 'url': '/muhasebe/tahsilat/'},
                {'label': 'Personel Ödemeleri', 'icon': 'bi-people', 'url': '/muhasebe/personel-odeme/'},
                {'label': 'Banka Hesapları', 'icon': 'bi-bank', 'url': '/muhasebe/banka/'},
                {'label': 'Raporlar', 'icon': 'bi-bar-chart-line', 'url': '/muhasebe/raporlar/'},
            ]},
            {'label': 'Devamsızlık', 'icon': 'bi-check2-square', 'url': '/devamsizlik/', 'modul_key': 'devamsizlik', 'children': [
                {'label': 'Yoklama Al', 'icon': 'bi-clipboard-check', 'url': '/devamsizlik/yoklama/',
                 'roller': ['admin', 'yonetici', 'ogretmen']},
                {'label': 'Devamsızlık Raporları', 'icon': 'bi-graph-up', 'url': '/devamsizlik/rapor/'},
            ]},
            {'label': 'Personel Yönetimi', 'icon': 'bi-person-badge', 'url': '/personel/', 'modul_key': 'personel', 'children': [
                {'label': 'Personel Listesi', 'icon': 'bi-people-fill', 'url': '/personel/personel/'},
                {'label': 'Yeni Personel', 'icon': 'bi-person-plus-fill', 'url': '/personel/personel/yeni'},
                {'label': 'İzin Yönetimi', 'icon': 'bi-calendar-check', 'url': '/personel/izin/'},
                {'label': 'Raporlar', 'icon': 'bi-bar-chart-line', 'url': '/personel/rapor/'},
            ]},
            {'label': 'Ders Dağıtımı', 'icon': 'bi-book', 'url': '/ders-dagitimi/', 'modul_key': 'ders_dagitimi', 'children': [
                {'label': 'Dersler', 'icon': 'bi-journal-text', 'url': '/ders-dagitimi/ders/',
                 'roller': ['admin', 'yonetici']},
                {'label': 'Ders Programı', 'icon': 'bi-calendar-week', 'url': '/ders-dagitimi/program/'},
                {'label': 'Öğretmen Ataması', 'icon': 'bi-person-workspace', 'url': '/ders-dagitimi/atama/',
                 'roller': ['admin', 'yonetici']},
            ]},
            {'label': 'Not Defteri', 'icon': 'bi-journal-bookmark', 'url': '/not-defteri/', 'modul_key': 'not_defteri', 'children': [
                {'label': 'Sınavlar', 'icon': 'bi-pencil-square', 'url': '/not-defteri/sinav/'},
                {'label': 'Not Girişi', 'icon': 'bi-input-cursor-text', 'url': '/not-defteri/sinav/'},
                {'label': 'Raporlar', 'icon': 'bi-file-earmark-bar-graph', 'url': '/not-defteri/rapor/'},
            ]},
            {'label': 'Ödev Takip', 'icon': 'bi-clipboard-check', 'url': '/odev/', 'modul_key': 'odev_takip', 'children': [
                {'label': 'Ödev Listesi', 'icon': 'bi-list-check', 'url': '/odev/liste'},
                {'label': 'Yeni Ödev', 'icon': 'bi-plus-circle', 'url': '/odev/yeni'},
                {'label': 'İstatistikler', 'icon': 'bi-bar-chart', 'url': '/odev/rapor/'},
            ]},
            {'label': 'Davranış Değerlendirme', 'icon': 'bi-emoji-smile', 'url': '/davranis/', 'modul_key': 'davranis', 'children': [
                {'label': 'Davranış Kayıtları', 'icon': 'bi-list-check', 'url': '/davranis/kayit/'},
                {'label': 'Yeni Kayıt', 'icon': 'bi-plus-circle', 'url': '/davranis/kayit/yeni'},
                {'label': 'Davranış Kuralları', 'icon': 'bi-shield-check', 'url': '/davranis/kural/'},
                {'label': 'Raporlar', 'icon': 'bi-bar-chart', 'url': '/davranis/rapor/'},
            ]},
            {'label': 'Karne / Transkript', 'icon': 'bi-file-earmark-text', 'url': '/karne/', 'modul_key': 'karne', 'children': [
                {'label': 'Karne Listesi', 'icon': 'bi-list-ul', 'url': '/karne/'},
                {'label': 'Karne Oluştur', 'icon': 'bi-plus-circle', 'url': '/karne/olustur'},
                {'label': 'Transkript', 'icon': 'bi-file-earmark-ruled', 'url': '/karne/transkript/'},
            ]},
            {'label': 'Etüt Yönetimi', 'icon': 'bi-book-half', 'url': '/etut/', 'modul_key': 'etut', 'children': [
                {'label': 'Etüt Listesi', 'icon': 'bi-list-ul', 'url': '/etut/'},
                {'label': 'Yeni Etüt', 'icon': 'bi-plus-circle', 'url': '/etut/yeni'},
                {'label': 'Raporlar', 'icon': 'bi-bar-chart', 'url': '/etut/rapor/'},
            ]},
            {'label': 'Sınav Oturum Yönetimi', 'icon': 'bi-calendar-check', 'url': '/sinav-oturum/oturum/', 'modul_key': 'sinav_oturum', 'children': [
                {'label': 'Oturum Listesi', 'icon': 'bi-list-ul', 'url': '/sinav-oturum/oturum/'},
                {'label': 'Yeni Oturum', 'icon': 'bi-plus-circle', 'url': '/sinav-oturum/oturum/yeni'},
                {'label': 'Sınav Takvimi', 'icon': 'bi-calendar-event', 'url': '/sinav-oturum/takvim/'},
            ]},
            {'label': 'Duyurular', 'icon': 'bi-megaphone', 'url': '/duyurular/', 'modul_key': 'duyurular', 'children': [
                {'label': 'Duyuru Listesi', 'icon': 'bi-card-text', 'url': '/duyurular/duyuru/'},
                {'label': 'Yeni Duyuru', 'icon': 'bi-plus-circle', 'url': '/duyurular/duyuru/yeni',
                 'roller': ['admin', 'yonetici', 'ogretmen', 'muhasebeci']},
                {'label': 'Etkinlik Takvimi', 'icon': 'bi-calendar-event', 'url': '/duyurular/etkinlik/'},
                {'label': 'Hatırlatmalar', 'icon': 'bi-bell', 'url': '/duyurular/hatirlatma/'},
            ]},
            {'label': 'Bildirim', 'icon': 'bi-bell-fill', 'url': '/bildirim/', 'modul_key': 'bildirim', 'children': [
                {'label': 'Gelen Bildirimler', 'icon': 'bi-inbox', 'url': '/bildirim/'},
                {'label': 'Özel Bildirim Gönder', 'icon': 'bi-send-plus', 'url': '/bildirim/ozel/',
                 'roller': ['admin', 'yonetici', 'muhasebeci', 'ogretmen']},
                {'label': 'Bildirim Şablonları', 'icon': 'bi-file-text', 'url': '/bildirim/sablon/',
                 'roller': ['admin', 'yonetici', 'muhasebeci', 'ogretmen']},
                {'label': 'Gönderim Geçmişi', 'icon': 'bi-clock-history', 'url': '/bildirim/ozel/gecmis',
                 'roller': ['admin', 'yonetici', 'muhasebeci', 'ogretmen']},
            ]},
            {'label': 'Rehberlik', 'icon': 'bi-heart-pulse', 'url': '/rehberlik/', 'modul_key': 'rehberlik', 'children': [
                {'label': 'Görüşmeler', 'icon': 'bi-chat-dots', 'url': '/rehberlik/gorusme/'},
                {'label': 'Öğrenci Profilleri', 'icon': 'bi-person-lines-fill', 'url': '/rehberlik/profil/'},
                {'label': 'Davranış Kayıtları', 'icon': 'bi-emoji-smile', 'url': '/davranis/kayit/'},
                {'label': 'Veli Görüşmeleri', 'icon': 'bi-people', 'url': '/rehberlik/veli/'},
                {'label': 'Rehberlik Planları', 'icon': 'bi-map', 'url': '/rehberlik/plan/'},
            ]},
            {'label': 'Sağlık', 'icon': 'bi-heart-pulse-fill', 'url': '/saglik/', 'modul_key': 'saglik', 'children': [
                {'label': 'Sağlık Kayıtları', 'icon': 'bi-file-medical', 'url': '/saglik/kayit/'},
                {'label': 'Revir', 'icon': 'bi-hospital', 'url': '/saglik/revir/'},
                {'label': 'Aşı Takip', 'icon': 'bi-shield-plus', 'url': '/saglik/asi/'},
                {'label': 'Sağlık Taraması', 'icon': 'bi-search-heart', 'url': '/saglik/tarama/'},
            ]},
            {'label': 'İletişim', 'icon': 'bi-chat-left-text', 'url': '/iletisim/', 'modul_key': 'iletisim', 'children': [
                {'label': 'Gelen Kutusu', 'icon': 'bi-inbox', 'url': '/iletisim/mesaj/'},
                {'label': 'Mesaj Yaz', 'icon': 'bi-pencil-square', 'url': '/iletisim/mesaj/yeni'},
                {'label': 'Toplu Mesaj', 'icon': 'bi-send', 'url': '/iletisim/toplu/',
                 'roller': ['admin', 'yonetici', 'ogretmen', 'muhasebeci']},
                {'label': 'Şablonlar', 'icon': 'bi-file-text', 'url': '/iletisim/sablon/',
                 'roller': ['admin', 'yonetici']},
                {'label': 'Rehber', 'icon': 'bi-person-rolodex', 'url': '/iletisim/rehber/',
                 'roller': ['admin', 'yonetici', 'ogretmen', 'muhasebeci']},
            ]},
            {'label': 'Online Sınav', 'icon': 'bi-laptop', 'url': '/online-sinav/', 'modul_key': 'online_sinav', 'children': [
                {'label': 'Sınav Listesi', 'icon': 'bi-list-check', 'url': '/online-sinav/sinav/'},
                {'label': 'Yeni Sınav', 'icon': 'bi-plus-circle', 'url': '/online-sinav/sinav/yeni',
                 'roller': ['admin', 'yonetici', 'ogretmen']},
                {'label': 'Sonuçlar', 'icon': 'bi-bar-chart', 'url': '/online-sinav/sonuc/'},
            ]},
            {'label': 'Kulüpler', 'icon': 'bi-people-fill', 'url': '/kulupler/', 'modul_key': 'kulupler', 'children': [
                {'label': 'Kulüp Listesi', 'icon': 'bi-list-ul', 'url': '/kulupler/kulup/'},
                {'label': 'Yeni Kulüp', 'icon': 'bi-plus-circle', 'url': '/kulupler/kulup/yeni'},
                {'label': 'Etkinlikler', 'icon': 'bi-calendar-event', 'url': '/kulupler/etkinlik/'},
            ]},
            {'label': 'Ortak Sınavlar', 'icon': 'bi-journal-text', 'url': '/ortak-sinav/sinav/', 'modul_key': 'ortak_sinav', 'children': [
                {'label': 'Sınav Listesi', 'icon': 'bi-list-ul', 'url': '/ortak-sinav/sinav/'},
                {'label': 'Yeni Sınav', 'icon': 'bi-plus-circle', 'url': '/ortak-sinav/sinav/yeni'},
                {'label': 'Raporlar', 'icon': 'bi-bar-chart', 'url': '/ortak-sinav/rapor/'},
            ]},
            {'label': 'Deneme Sınavları', 'icon': 'bi-bar-chart-line', 'url': '/deneme-sinavi/sinav/', 'modul_key': 'deneme_sinavi', 'children': [
                {'label': 'Sınav Listesi', 'icon': 'bi-list-ul', 'url': '/deneme-sinavi/sinav/'},
                {'label': 'Yeni Deneme', 'icon': 'bi-plus-circle', 'url': '/deneme-sinavi/sinav/yeni'},
            ]},
            {'label': 'Online Anket', 'icon': 'bi-ui-checks-grid', 'url': '/anket/yonetim/', 'modul_key': 'anket', 'children': [
                {'label': 'Anket Listesi', 'icon': 'bi-list-ul', 'url': '/anket/yonetim/',
                 'roller': ['admin', 'yonetici', 'ogretmen', 'muhasebeci']},
                {'label': 'Yeni Anket', 'icon': 'bi-plus-circle', 'url': '/anket/yonetim/yeni',
                 'roller': ['admin', 'yonetici', 'ogretmen']},
                {'label': 'Aktif Anketler', 'icon': 'bi-check-circle', 'url': '/anket/katilim/'},
            ]},
            {'label': 'Öğrenci Servisi', 'icon': 'bi-bus-front', 'url': '/servis/', 'modul_key': 'servis', 'children': [
                {'label': 'Güzergahlar', 'icon': 'bi-signpost-2', 'url': '/servis/guzergah/'},
                {'label': 'Araçlar', 'icon': 'bi-bus-front', 'url': '/servis/arac/'},
                {'label': 'Kayıtlar', 'icon': 'bi-people', 'url': '/servis/kayit/'},
            ]},
            {'label': 'Kantin / Yemekhane', 'icon': 'bi-cup-hot', 'url': '/kantin/', 'modul_key': 'kantin', 'children': [
                {'label': 'Yemek Menüleri', 'icon': 'bi-calendar-week', 'url': '/kantin/menu/'},
                {'label': 'Haftalık Menü', 'icon': 'bi-table', 'url': '/kantin/menu/haftalik'},
                {'label': 'Ürünler', 'icon': 'bi-basket', 'url': '/kantin/urun/'},
                {'label': 'Satış', 'icon': 'bi-cart', 'url': '/kantin/satis/yeni'},
            ]},
            {'label': 'Kütüphane', 'icon': 'bi-book', 'url': '/kutuphane/', 'modul_key': 'kutuphane', 'children': [
                {'label': 'Kitaplar', 'icon': 'bi-book', 'url': '/kutuphane/kitap/'},
                {'label': 'Yeni Kitap', 'icon': 'bi-plus-circle', 'url': '/kutuphane/kitap/yeni'},
                {'label': 'Ödünç Kayıtları', 'icon': 'bi-arrow-left-right', 'url': '/kutuphane/odunc/'},
            ]},
            {'label': 'Envanter / Demirbaş', 'icon': 'bi-box-seam', 'url': '/envanter/', 'modul_key': 'envanter', 'children': [
                {'label': 'Demirbaşlar', 'icon': 'bi-list-ul', 'url': '/envanter/demirbas/'},
                {'label': 'Yeni Demirbaş', 'icon': 'bi-plus-circle', 'url': '/envanter/demirbas/yeni'},
            ]},
            {'label': 'Yurt / Pansiyon', 'icon': 'bi-house-door', 'url': '/yurt/', 'modul_key': 'yurt', 'children': [
                {'label': 'Odalar', 'icon': 'bi-door-open', 'url': '/yurt/oda/'},
                {'label': 'Yeni Oda', 'icon': 'bi-plus-circle', 'url': '/yurt/oda/yeni'},
                {'label': 'Yoklama', 'icon': 'bi-clipboard-check', 'url': '/yurt/yoklama/'},
            ]},
            {'label': 'Ders Programı', 'icon': 'bi-calendar-week', 'url': '/ders-programi/', 'modul_key': 'ders_programi', 'children': [
                {'label': 'Şube Programı', 'icon': 'bi-table', 'url': '/ders-programi/'},
                {'label': 'Öğretmen Programı', 'icon': 'bi-person-workspace', 'url': '/ders-programi/ogretmen'},
            ]},
            {'label': 'Raporlama', 'icon': 'bi-graph-up-arrow', 'url': '/raporlama/', 'modul_key': 'raporlama', 'children': [
                {'label': 'Dashboard', 'icon': 'bi-speedometer2', 'url': '/raporlama/'},
                {'label': 'Öğrenci Rapor', 'icon': 'bi-people', 'url': '/raporlama/ogrenci/'},
                {'label': 'Personel Rapor', 'icon': 'bi-person-badge', 'url': '/raporlama/personel/'},
                {'label': 'Akademik Rapor', 'icon': 'bi-mortarboard', 'url': '/raporlama/akademik/'},
            ]},
            {'label': 'Denetim Kaydı', 'icon': 'bi-shield-check', 'url': '/denetim/', 'modul_key': 'denetim', 'children': [
                {'label': 'Log Kayıtları', 'icon': 'bi-list-check', 'url': '/denetim/'},
            ]},
            {'label': 'Belge Yönetimi', 'icon': 'bi-file-earmark', 'url': '/belge/', 'modul_key': 'belge', 'children': [
                {'label': 'Belgeler', 'icon': 'bi-files', 'url': '/belge/'},
                {'label': 'Yeni Belge', 'icon': 'bi-plus-circle', 'url': '/belge/yeni',
                 'roller': ['admin', 'yonetici']},
            ]},
            {'label': 'Sistem Ayarları', 'icon': 'bi-gear', 'url': '/ayarlar/', 'modul_key': 'ayarlar', 'children': [
                {'label': 'Genel Ayarlar', 'icon': 'bi-sliders', 'url': '/ayarlar/genel',
                 'roller': ['admin']},
                {'label': 'Akademik', 'icon': 'bi-mortarboard', 'url': '/ayarlar/akademik',
                 'roller': ['admin']},
                {'label': 'Yedekleme', 'icon': 'bi-download', 'url': '/ayarlar/yedekleme',
                 'roller': ['admin', 'yonetici']},
                {'label': 'Rol Yetkilendirme', 'icon': 'bi-shield-lock', 'url': '/ayarlar/yetkilendirme/',
                 'roller': ['admin']},
            ]},
        ]

        # Dinamik izin kontrolü ile menü filtrele
        if current_user.is_authenticated:
            from app.module_registry import modul_renk_kategorisi, url_to_modul_key

            # Turkce karakterleri normalize ederek alfabetik siralama anahtari
            def _menu_sort_key(s: str) -> str:
                s = (s or '').lower()
                tr_map = {'ı': 'i', 'i̇': 'i', 'ş': 's', 'ğ': 'g',
                          'ü': 'u', 'ö': 'o', 'ç': 'c'}
                for tr, en in tr_map.items():
                    s = s.replace(tr, en)
                return s

            # Ilk kurulumda varsayilan izinleri olustur. Ayrica yeni modul
            # eklendiyse (MODULLER'de olup DB'de kaydi olmayan) eksikleri tamamla.
            # Fonksiyon idempotenttir: mevcut kayitlara dokunmaz.
            toplam_olmasi_gereken = len(RolModulIzin.MODULLER) * len(RolModulIzin.ROLLER)
            if RolModulIzin.query.count() < toplam_olmasi_gereken:
                RolModulIzin.varsayilan_izinleri_olustur()

            # Kullanicinin erisebildigi modulleri
            izinli_moduller = current_user.erisebildigi_moduller()

            kullanici_rolu = getattr(current_user, 'rol', None)
            menu_items = []
            for item in all_menu_items:
                modul_key = item.get('modul_key')
                if modul_key is None:
                    menu_items.append(item)
                elif modul_key in izinli_moduller:
                    # Renk kategorisi ekle
                    item['renk_kat'] = modul_renk_kategorisi(modul_key)
                    # Cocuklari role gore filtrele (opsiyonel 'roller' alani) +
                    # alt menuyu de A-Z sirala
                    cocuklar = item.get('children') or []
                    if cocuklar and kullanici_rolu:
                        filtrelenmis = [
                            c for c in cocuklar
                            if 'roller' not in c or kullanici_rolu in c['roller']
                        ]
                        item['children'] = filtrelenmis
                    if item.get('children'):
                        item['children'] = sorted(
                            item['children'],
                            key=lambda c: _menu_sort_key(c.get('label', '')),
                        )
                    menu_items.append(item)

            # Ana menu bagliklarini A-Z sirala (Turkce karakter normalize)
            menu_items = sorted(
                menu_items,
                key=lambda i: _menu_sort_key(i.get('label', '')),
            )

            # Aktif sayfanin modul rengini hesapla (sidebar + page header icin)
            aktif_modul = url_to_modul_key(request.path)
            aktif_renk = modul_renk_kategorisi(aktif_modul) if aktif_modul else ''
        else:
            menu_items = []
            aktif_renk = ''

        return dict(menu_items=menu_items, aktif_renk=aktif_renk)

    # Seed komutu
    @app.cli.command('seed')
    def seed_command():
        """Veritabanına başlangıç verisi ekle (sadece admin + sistem ayarları)."""
        from app.models.user import User
        from app.models.muhasebe import GelirGiderKategorisi, BankaHesabi

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


        # === Sistem Ayarlari seed verisi ===
        from app.models.ayarlar import SistemAyar

        if SistemAyar.query.count() == 0:
            varsayilan_ayarlar = [
                # Genel
                ('kurum_adi', 'OBS Egitim Kurumu', 'Kurum Adi', 'genel', 'text', 'OBS Egitim Kurumu'),
                ('aktif_donem', '2025-2026', 'Aktif Donem', 'genel', 'text', '2025-2026'),
                ('varsayilan_dil', 'tr', 'Varsayilan Dil', 'genel', 'text', 'tr'),
                ('zaman_dilimi', 'Europe/Istanbul', 'Zaman Dilimi', 'genel', 'text', 'Europe/Istanbul'),
                # Akademik
                ('gecme_notu', '50', 'Gecme Notu', 'akademik', 'number', '50'),
                ('not_sistemi', '100', 'Not Sistemi', 'akademik', 'number', '100'),
                ('max_devamsizlik_gun', '20', 'Maks. Devamsizlik Gun', 'akademik', 'number', '20'),
                ('sinav_agirlik_yazili', '60', 'Yazili Sinav Agirligi (%)', 'akademik', 'number', '60'),
                ('sinav_agirlik_sozlu', '20', 'Sozlu Sinav Agirligi (%)', 'akademik', 'number', '20'),
                ('sinav_agirlik_performans', '20', 'Performans Agirligi (%)', 'akademik', 'number', '20'),
                # Muhasebe
                ('para_birimi', 'TL', 'Para Birimi', 'muhasebe', 'text', 'TL'),
                ('kdv_orani', '0', 'KDV Orani (%)', 'muhasebe', 'number', '0'),
                ('gecikme_faizi', '0', 'Gecikme Faizi (%)', 'muhasebe', 'number', '0'),
                ('odeme_hatirlatma_gun', '7', 'Odeme Hatirlatma (Gun)', 'muhasebe', 'number', '7'),
                ('taksit_otomatik_hatirlatma_aktif', 'false',
                 'Geciken Taksit Otomatik Hatirlatma', 'muhasebe', 'boolean', 'false'),
                ('taksit_hatirlatma_periyot_gun', '7',
                 'Geciken Taksit Hatirlatma Periyodu (Gun)', 'muhasebe', 'number', '7'),
                ('taksit_hatirlatma_ilk_gun', '0',
                 'Vade Gecince Ilk Hatirlatma (Gun)', 'muhasebe', 'number', '0'),
                # Iletisim
                ('sms_saglayici', 'yok', 'SMS Saglayici', 'iletisim', 'text', 'yok'),
                ('bildirim_email', 'info@obs.local', 'Bildirim E-posta Adresi', 'iletisim', 'email', 'info@obs.local'),
                ('otomatik_bildirim', 'true', 'Otomatik Bildirim', 'iletisim', 'boolean', 'true'),
                # Guvenlik
                ('oturum_suresi', '60', 'Oturum Suresi (dk)', 'guvenlik', 'number', '60'),
                ('min_sifre_uzunlugu', '6', 'Min. Sifre Uzunlugu', 'guvenlik', 'number', '6'),
                ('max_giris_denemesi', '5', 'Maks. Giris Denemesi', 'guvenlik', 'number', '5'),
            ]
            for anahtar, deger, aciklama, kategori, tur, varsayilan in varsayilan_ayarlar:
                db.session.add(SistemAyar(
                    anahtar=anahtar,
                    deger=deger,
                    aciklama=aciklama,
                    kategori=kategori,
                    tur=tur,
                    varsayilan=varsayilan,
                ))
            db.session.commit()

        # === Yeni eklenen SistemAyar anahtarlari (eski tenantlar icin backfill) ===
        # Idempotent: sadece eksik olanlari ekler, mevcut degerleri bozmaz.
        yeni_anahtarlar = [
            ('taksit_otomatik_hatirlatma_aktif', 'false',
             'Geciken Taksit Otomatik Hatirlatma', 'muhasebe', 'boolean', 'false'),
            ('taksit_hatirlatma_periyot_gun', '7',
             'Geciken Taksit Hatirlatma Periyodu (Gun)', 'muhasebe', 'number', '7'),
            ('taksit_hatirlatma_ilk_gun', '0',
             'Vade Gecince Ilk Hatirlatma (Gun)', 'muhasebe', 'number', '0'),
        ]
        eklendi = False
        for anahtar, deger, aciklama, kategori, tur, varsayilan in yeni_anahtarlar:
            if not SistemAyar.query.filter_by(anahtar=anahtar).first():
                db.session.add(SistemAyar(
                    anahtar=anahtar, deger=deger, aciklama=aciklama,
                    kategori=kategori, tur=tur, varsayilan=varsayilan,
                ))
                eklendi = True
        if eklendi:
            db.session.commit()


        # === Bildirim sistem sablonlari ===
        from app.models.bildirim import BildirimSablonu
        sistem_sablonlar = [
            ('Dogum Gunu Kutlamasi', 'Dogum Gunun Kutlu Olsun {ad}!',
             'Sevgili {ad} {soyad}, dogum gununu tum kalbimizle kutlariz. '
             'Saglik, basari ve mutluluk dolu bir yas dilriz.',
             'dogum_gunu', '/bildirim/'),
            ('Taksit Hatirlatma',
             '{ad} {soyad} - Yaklasan Taksit',
             'Sayin veli, {ad} {soyad} icin {vade} tarihinde {tutar} TL '
             'taksit odemesi bulunmaktadir. Odeme icin muhasebeye '
             'ulasabilirsiniz.',
             'taksit_hatirlatma', '/portal/muhasebe/'),
            ('Veli Gorusme Daveti',
             'Veli Gorusmesi Daveti - {ad} {soyad}',
             'Sayin {veli_ad} {veli_soyad}, {ad} {soyad} hakkinda '
             'gorusmek uzere okulumuza davet ediyoruz. Randevu icin '
             'rehberlik servisiyle iletisime gecebilirsiniz.',
             'veli_gorusme', '/portal/veli/'),
            ('Genel Duyuru',
             'Onemli Duyuru',
             'Sayin ilgili, onemli bir duyurumuz bulunmaktadir. '
             'Detaylar icin lutfen okul sistemine giris yapiniz.',
             'genel', '/duyurular/'),
        ]
        for ad, baslik, mesaj, kat, link in sistem_sablonlar:
            if not BildirimSablonu.query.filter_by(ad=ad, sistem=True).first():
                db.session.add(BildirimSablonu(
                    ad=ad, baslik=baslik, mesaj=mesaj,
                    kategori=kat, link=link, sistem=True, aktif=True,
                ))

        db.session.commit()
        print('Başlangıç verisi başarıyla eklendi!')

    # Kayitsiz ogrencileri bir donem+sube'ye atama komutu
    import click

    @app.cli.command('kayitsiz-ogrencileri-kaydet')
    @click.option('--donem-id', type=int, required=True, help='KayitDonemi ID')
    @click.option('--sube-id', type=int, required=True, help='Sube ID')
    def kayitsiz_kaydet_command(donem_id, sube_id):
        """Aktif OgrenciKayit kaydi olmayan tum ogrencileri verilen
        donem ve subeye aktif olarak kaydet."""
        from app.models.user import User
        from app.models.muhasebe import Ogrenci
        from app.models.kayit import KayitDonemi, Sube, OgrenciKayit
        from datetime import date

        donem = KayitDonemi.query.get(donem_id)
        sube = Sube.query.get(sube_id)
        if not donem:
            click.echo(f'Donem #{donem_id} bulunamadi.')
            return
        if not sube:
            click.echo(f'Sube #{sube_id} bulunamadi.')
            return

        # Admin kullanicisini olusturan olarak ata
        admin = User.query.filter_by(rol='admin').first()
        if not admin:
            click.echo('Admin kullanici bulunamadi.')
            return

        eklenen = 0
        for o in Ogrenci.query.all():
            aktif_k = OgrenciKayit.query.filter_by(
                ogrenci_id=o.id, durum='aktif'
            ).first()
            if aktif_k:
                continue
            kayit = OgrenciKayit(
                ogrenci_id=o.id,
                donem_id=donem.id,
                sube_id=sube.id,
                kayit_tarihi=date.today(),
                durum='aktif',
                olusturan_id=admin.id,
            )
            db.session.add(kayit)
            # Sinif alani bossa doldur
            if not o.sinif:
                o.sinif = sube.sinif.ad
            eklenen += 1
            click.echo(f'  {o.tam_ad} ({o.ogrenci_no}) -> {donem.ad} / {sube.tam_ad}')

        db.session.commit()
        click.echo(f'\nToplam {eklenen} ogrenci kaydedildi.')

    # Ogrenci.sinif string alanini aktif OgrenciKayit.sube.sinif.ad ile senkronla
    @app.cli.command('ogrenci-sinif-senkronla')
    def ogrenci_sinif_senkronla_command():
        """Her aktif OgrenciKayit icin Ogrenci.sinif alanini
        kayit.sube.sinif.ad degeri ile eszaman eder. Boylece kayit listesi ile
        muhasebe ekranlarinda ayni sinif bilgisi gorunur."""
        from app.models.muhasebe import Ogrenci
        from app.models.kayit import OgrenciKayit

        duzeltilen = 0
        for o in Ogrenci.query.all():
            aktif_k = OgrenciKayit.query.filter_by(
                ogrenci_id=o.id, durum='aktif'
            ).first()
            if not aktif_k or not aktif_k.sube:
                continue
            dogru_deger = aktif_k.sube.sinif.ad
            if o.sinif != dogru_deger:
                click.echo(
                    f'  {o.tam_ad} ({o.ogrenci_no}): "{o.sinif}" -> "{dogru_deger}"'
                )
                o.sinif = dogru_deger
                duzeltilen += 1

        db.session.commit()
        click.echo(f'\nToplam {duzeltilen} ogrencinin sinif bilgisi senkronlandi.')

    # Portal hesaplari icin backfill komutu
    @app.cli.command('portal-backfill')
    def portal_backfill_command():
        """Eski kayitlari tarayip user_id'si olmayan Ogrenci ve VeliBilgisi
        kayitlari icin kullanici hesaplari olusturur."""
        from app.models.user import User
        from app.models.muhasebe import Ogrenci
        from app.models.kayit import VeliBilgisi

        olusturulan_ogrenci = 0
        olusturulan_veli = 0
        hatalar = []

        # === Ogrenciler ===
        ogrenciler = Ogrenci.query.filter(Ogrenci.user_id.is_(None)).all()
        for o in ogrenciler:
            username = o.ogrenci_no
            if not username:
                hatalar.append(f'Ogrenci #{o.id} ({o.tam_ad}) icin ogrenci_no bos — atlandi.')
                continue
            if User.query.filter_by(username=username).first():
                hatalar.append(f'Ogrenci #{o.id}: "{username}" kullanici adi zaten kullanimda — atlandi.')
                continue
            sifre = o.tc_kimlik if o.tc_kimlik else username
            email = o.email or f'{username}@ogrenci.obs'
            # Email cakismasi kontrolu
            if User.query.filter_by(email=email).first():
                email = f'{username}@ogrenci.obs'
                if User.query.filter_by(email=email).first():
                    email = f'{username}_{o.id}@ogrenci.obs'
            user = User(
                username=username,
                email=email,
                ad=o.ad,
                soyad=o.soyad,
                rol='ogrenci',
                aktif=True,
            )
            user.set_password(sifre)
            db.session.add(user)
            db.session.flush()
            o.user_id = user.id
            olusturulan_ogrenci += 1
            print(f'[Ogrenci] {o.tam_ad} -> kullanici: {username} / sifre: {sifre}')

        # === Veliler ===
        veliler = VeliBilgisi.query.filter(VeliBilgisi.user_id.is_(None)).all()
        for v in veliler:
            ogrenci = v.ogrenci
            if not ogrenci:
                hatalar.append(f'Veli #{v.id} ({v.tam_ad}) icin ogrenci bulunamadi — atlandi.')
                continue
            username = f'veli_{ogrenci.ogrenci_no}_{v.yakinlik}'
            if User.query.filter_by(username=username).first():
                username = f'{username}_{v.id}'
            sifre = v.tc_kimlik if v.tc_kimlik else username
            email = v.email or f'{username}@veli.obs'
            if User.query.filter_by(email=email).first():
                email = f'{username}@veli.obs'
                if User.query.filter_by(email=email).first():
                    email = f'{username}_{v.id}@veli.obs'
            user = User(
                username=username,
                email=email,
                ad=v.ad,
                soyad=v.soyad,
                rol='veli',
                aktif=True,
            )
            user.set_password(sifre)
            db.session.add(user)
            db.session.flush()
            v.user_id = user.id
            olusturulan_veli += 1
            print(f'[Veli]    {v.tam_ad} ({ogrenci.tam_ad}) -> kullanici: {username} / sifre: {sifre}')

        db.session.commit()

        print('')
        print('=' * 60)
        print(f'Backfill tamamlandi:')
        print(f'  Olusturulan ogrenci hesabi : {olusturulan_ogrenci}')
        print(f'  Olusturulan veli hesabi    : {olusturulan_veli}')
        if hatalar:
            print(f'  Uyarilar / atlananlar      : {len(hatalar)}')
            for h in hatalar:
                print(f'    - {h}')
        print('=' * 60)

    @app.cli.command('deneme-puan-yenile')
    @click.option('--sinav-id', type=int, default=None,
                  help='Sadece bu sinav icin yeniden hesapla (varsayilan: tumu)')
    def deneme_puan_yenile_command(sinav_id):
        """Tum DenemeKatilim kayitlari icin toplam_net ve toplam_puan'i yeniden hesaplar.

        alan/tipi uyumsuzlugu nedeniyle puani 100 sabit kalan kayitlari
        duzeltir (fallback formul devreye girer).
        """
        from app.models.deneme_sinavi import DenemeKatilim, DenemeSinavi
        from app.deneme_sinavi.hesaplar import guncelle_katilim_toplamlari

        q = DenemeKatilim.query.filter_by(katildi=True)
        if sinav_id:
            q = q.filter_by(deneme_sinavi_id=sinav_id)
        katilimlar = q.all()
        click.echo(f'{len(katilimlar)} katilim yeniden hesaplanacak...')
        degisen = 0
        for k in katilimlar:
            eski = k.toplam_puan
            guncelle_katilim_toplamlari(k)
            if eski != k.toplam_puan:
                degisen += 1
        db.session.commit()
        click.echo(f'  Tamam: {degisen} katilimin puani guncellendi.')

    @app.cli.command('risk-snapshot')
    @click.option('--force', is_flag=True, default=False,
                  help='Bugun mevcut snapshot varsa uzerine yaz')
    def risk_snapshot_command(force):
        """Tum aktif ogrenciler icin gunun risk skoru snapshot'ini kaydeder.

        Haftalik cron olarak calismasi onerilir:
            0 6 * * 1  flask risk-snapshot
        """
        from app.rehberlik.risk_skoru import risk_snapshot_toplu
        sonuc = risk_snapshot_toplu(force=force)
        click.echo(f"Risk snapshot - {sonuc['tarih'].strftime('%d.%m.%Y')}")
        click.echo(f"  Toplam aktif ogrenci   : {sonuc['toplam']}")
        click.echo(f"  Olusturulan            : {sonuc['olusturulan']}")
        click.echo(f"  Guncellenen            : {sonuc['guncellenen']}")
        click.echo(f"  Es gecilen (mevcut)    : {sonuc['es_gecilen']}")

    return app
