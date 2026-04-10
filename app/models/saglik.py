from datetime import datetime, date
from app.extensions import db


class SaglikKaydi(db.Model):
    """Ogrenci Saglik Kaydi (Health Record)"""
    __tablename__ = 'saglik_kayitlari'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False, unique=True)
    kan_grubu = db.Column(db.String(5), nullable=True)
    # A+, A-, B+, B-, AB+, AB-, 0+, 0-
    boy = db.Column(db.Float, nullable=True)  # cm
    kilo = db.Column(db.Float, nullable=True)  # kg
    kronik_hastalik = db.Column(db.Text, nullable=True)
    alerji = db.Column(db.Text, nullable=True)
    surekli_ilac = db.Column(db.Text, nullable=True)
    engel_durumu = db.Column(db.String(20), nullable=False, default='yok')
    # yok, fiziksel, zihinsel, gorme, isitme, diger
    ozel_not = db.Column(db.Text, nullable=True)
    acil_kisi_adi = db.Column(db.String(100), nullable=True)
    acil_kisi_telefon = db.Column(db.String(20), nullable=True)
    acil_kisi_yakinlik = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('saglik_kaydi', uselist=False))

    @property
    def kan_grubu_str(self):
        return self.kan_grubu or 'Belirtilmemiş'

    @property
    def engel_durumu_str(self):
        engel_map = {
            'yok': 'Yok',
            'fiziksel': 'Fiziksel',
            'zihinsel': 'Zihinsel',
            'gorme': 'Görme',
            'isitme': 'İşitme',
            'diger': 'Diğer',
        }
        return engel_map.get(self.engel_durumu, self.engel_durumu)

    @property
    def bmi(self):
        if self.boy and self.kilo and self.boy > 0:
            boy_m = self.boy / 100
            return round(self.kilo / (boy_m * boy_m), 1)
        return None

    def __repr__(self):
        return f'<SaglikKaydi ogrenci_id={self.ogrenci_id}>'


class RevirKaydi(db.Model):
    """Revir Kaydi (Infirmary Record)"""
    __tablename__ = 'revir_kayitlari'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    tarih = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    sikayet = db.Column(db.Text, nullable=False)
    yapilan_islem = db.Column(db.Text, nullable=False)
    verilen_ilac = db.Column(db.String(200), nullable=True)
    sonuc = db.Column(db.String(30), nullable=False, default='sinifa_dondu')
    # taburcu, veliye_teslim, hastaneye_sevk, sinifa_dondu
    ilgilenen_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('revir_kayitlari', lazy='dynamic'))
    ilgilenen = db.relationship('User', backref=db.backref('revir_kayitlari', lazy='dynamic'))

    @property
    def sonuc_str(self):
        sonuc_map = {
            'taburcu': 'Taburcu',
            'veliye_teslim': 'Veliye Teslim',
            'hastaneye_sevk': 'Hastaneye Sevk',
            'sinifa_dondu': 'Sınıfa Döndü',
        }
        return sonuc_map.get(self.sonuc, self.sonuc)

    @property
    def sonuc_badge(self):
        badge_map = {
            'taburcu': 'info',
            'veliye_teslim': 'warning',
            'hastaneye_sevk': 'danger',
            'sinifa_dondu': 'success',
        }
        return badge_map.get(self.sonuc, 'secondary')

    def __repr__(self):
        return f'<RevirKaydi id={self.id} ogrenci_id={self.ogrenci_id}>'


class AsiTakip(db.Model):
    """Asi Takip (Vaccination Tracking)"""
    __tablename__ = 'asi_takip'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    asi_adi = db.Column(db.String(100), nullable=False)
    asi_tarihi = db.Column(db.Date, nullable=False)
    hatirlatma_tarihi = db.Column(db.Date, nullable=True)
    durum = db.Column(db.String(20), nullable=False, default='yapildi')
    # yapildi, bekliyor, gecikti
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('asi_kayitlari', lazy='dynamic'))

    @property
    def durum_str(self):
        durum_map = {
            'yapildi': 'Yapıldı',
            'bekliyor': 'Bekliyor',
            'gecikti': 'Gecikti',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        badge_map = {
            'yapildi': 'success',
            'bekliyor': 'warning',
            'gecikti': 'danger',
        }
        return badge_map.get(self.durum, 'secondary')

    def __repr__(self):
        return f'<AsiTakip id={self.id} asi={self.asi_adi}>'


class SaglikTaramasi(db.Model):
    """Saglik Taramasi (Health Screening)"""
    __tablename__ = 'saglik_taramalari'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    tarama_tarihi = db.Column(db.Date, nullable=False)
    tarama_turu = db.Column(db.String(20), nullable=False)
    # goz, kulak, dis, genel, boy_kilo, skolyoz
    sonuc = db.Column(db.String(20), nullable=False, default='normal')
    # normal, anormal, tedavi_gerekli
    bulgular = db.Column(db.Text, nullable=False)
    oneri = db.Column(db.Text, nullable=True)
    tarayan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('saglik_taramalari', lazy='dynamic'))
    tarayan = db.relationship('User', backref=db.backref('saglik_taramalari', lazy='dynamic'))

    @property
    def tarama_turu_str(self):
        tur_map = {
            'goz': 'Göz',
            'kulak': 'Kulak',
            'dis': 'Diş',
            'genel': 'Genel',
            'boy_kilo': 'Boy/Kilo',
            'skolyoz': 'Skolyoz',
        }
        return tur_map.get(self.tarama_turu, self.tarama_turu)

    @property
    def sonuc_str(self):
        sonuc_map = {
            'normal': 'Normal',
            'anormal': 'Anormal',
            'tedavi_gerekli': 'Tedavi Gerekli',
        }
        return sonuc_map.get(self.sonuc, self.sonuc)

    @property
    def sonuc_badge(self):
        badge_map = {
            'normal': 'success',
            'anormal': 'warning',
            'tedavi_gerekli': 'danger',
        }
        return badge_map.get(self.sonuc, 'secondary')

    @property
    def tarama_turu_icon(self):
        icon_map = {
            'goz': 'bi-eye',
            'kulak': 'bi-ear',
            'dis': 'bi-emoji-smile',
            'genel': 'bi-heart-pulse',
            'boy_kilo': 'bi-rulers',
            'skolyoz': 'bi-person-standing',
        }
        return icon_map.get(self.tarama_turu, 'bi-heart-pulse')

    def __repr__(self):
        return f'<SaglikTaramasi id={self.id} tur={self.tarama_turu}>'
