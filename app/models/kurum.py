from datetime import datetime, date
from app.extensions import db


class Kurum(db.Model):
    __tablename__ = 'kurumlar'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(200), nullable=False)
    kisa_ad = db.Column(db.String(50), nullable=True)
    kurum_turu = db.Column(db.String(20), nullable=False, default='lise')
    kurum_kodu = db.Column(db.String(50), nullable=True)
    telefon = db.Column(db.String(20), nullable=True)
    fax = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    web_sitesi = db.Column(db.String(200), nullable=True)
    adres = db.Column(db.Text, nullable=True)
    il = db.Column(db.String(50), nullable=True)
    ilce = db.Column(db.String(50), nullable=True)
    posta_kodu = db.Column(db.String(10), nullable=True)
    vergi_dairesi = db.Column(db.String(100), nullable=True)
    vergi_no = db.Column(db.String(20), nullable=True)
    mudur_adi = db.Column(db.String(150), nullable=True)
    mudur_telefon = db.Column(db.String(20), nullable=True)
    logo_url = db.Column(db.String(300), nullable=True)
    slogan = db.Column(db.String(300), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    KURUM_TURU_CHOICES = [
        ('ilkokul', 'Ilkokul'),
        ('ortaokul', 'Ortaokul'),
        ('lise', 'Lise'),
        ('kolej', 'Kolej'),
        ('kurs', 'Kurs'),
    ]

    @property
    def kurum_turu_str(self):
        tur_map = dict(self.KURUM_TURU_CHOICES)
        return tur_map.get(self.kurum_turu, self.kurum_turu)

    def __repr__(self):
        return f'<Kurum {self.ad}>'


class OgretimYili(db.Model):
    __tablename__ = 'ogretim_yillari'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(50), nullable=False)
    baslangic_tarihi = db.Column(db.Date, nullable=False)
    bitis_tarihi = db.Column(db.Date, nullable=False)
    yariyil_baslangic = db.Column(db.Date, nullable=True)
    yariyil_bitis = db.Column(db.Date, nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tatiller = db.relationship('Tatil', backref='ogretim_yili', lazy='dynamic')

    def __repr__(self):
        return f'<OgretimYili {self.ad}>'


class Tatil(db.Model):
    __tablename__ = 'tatiller'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(150), nullable=False)
    baslangic_tarihi = db.Column(db.Date, nullable=False)
    bitis_tarihi = db.Column(db.Date, nullable=False)
    tur = db.Column(db.String(20), nullable=False, default='resmi_tatil')
    ogretim_yili_id = db.Column(db.Integer, db.ForeignKey('ogretim_yillari.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    TUR_CHOICES = [
        ('resmi_tatil', 'Resmi Tatil'),
        ('ara_tatil', 'Ara Tatil'),
        ('sinav_haftasi', 'Sinav Haftasi'),
        ('diger', 'Diger'),
    ]

    @property
    def tur_str(self):
        tur_map = dict(self.TUR_CHOICES)
        return tur_map.get(self.tur, self.tur)

    @property
    def tur_badge(self):
        badge_map = {
            'resmi_tatil': 'danger',
            'ara_tatil': 'warning',
            'sinav_haftasi': 'info',
            'diger': 'secondary',
        }
        return badge_map.get(self.tur, 'secondary')

    @property
    def gun_sayisi(self):
        return (self.bitis_tarihi - self.baslangic_tarihi).days + 1

    def __repr__(self):
        return f'<Tatil {self.ad}>'


class Derslik(db.Model):
    __tablename__ = 'derslikler'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(50), nullable=False)
    kat = db.Column(db.Integer, nullable=True)
    kapasite = db.Column(db.Integer, nullable=True)
    tur = db.Column(db.String(20), nullable=False, default='sinif')
    donanim = db.Column(db.Text, nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    TUR_CHOICES = [
        ('sinif', 'Sinif'),
        ('lab', 'Laboratuvar'),
        ('spor_salonu', 'Spor Salonu'),
        ('konferans', 'Konferans Salonu'),
        ('kutuphane', 'Kutuphane'),
        ('diger', 'Diger'),
    ]

    @property
    def tur_str(self):
        tur_map = dict(self.TUR_CHOICES)
        return tur_map.get(self.tur, self.tur)

    @property
    def tur_badge(self):
        badge_map = {
            'sinif': 'primary',
            'lab': 'success',
            'spor_salonu': 'warning',
            'konferans': 'info',
            'kutuphane': 'secondary',
            'diger': 'dark',
        }
        return badge_map.get(self.tur, 'secondary')

    def __repr__(self):
        return f'<Derslik {self.ad}>'
