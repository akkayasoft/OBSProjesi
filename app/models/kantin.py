from datetime import datetime, date
from app.extensions import db


class YemekMenu(db.Model):
    __tablename__ = 'yemek_menuleri'

    id = db.Column(db.Integer, primary_key=True)
    tarih = db.Column(db.Date, nullable=False, unique=True)
    gun = db.Column(db.String(20), nullable=False)
    kahvalti = db.Column(db.Text, nullable=True)
    ogle_yemegi = db.Column(db.Text, nullable=False)
    ara_ogun = db.Column(db.Text, nullable=True)
    kalori = db.Column(db.Integer, nullable=True)
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    GUNLER = ['Pazartesi', 'Sali', 'Carsamba', 'Persembe', 'Cuma']

    def __repr__(self):
        return f'<YemekMenu {self.tarih}>'


class KantinUrun(db.Model):
    __tablename__ = 'kantin_urunler'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(200), nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    fiyat = db.Column(db.Float, nullable=False)
    stok = db.Column(db.Integer, nullable=False, default=0)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    satislar = db.relationship('KantinSatis', backref='urun', lazy='dynamic')

    KATEGORILER = [
        ('yiyecek', 'Yiyecek'),
        ('icecek', 'Icecek'),
        ('atistirmalik', 'Atistirmalik'),
    ]

    @property
    def kategori_str(self):
        return dict(self.KATEGORILER).get(self.kategori, self.kategori)

    def __repr__(self):
        return f'<KantinUrun {self.ad}>'


class KantinSatis(db.Model):
    __tablename__ = 'kantin_satislar'

    id = db.Column(db.Integer, primary_key=True)
    urun_id = db.Column(db.Integer, db.ForeignKey('kantin_urunler.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=True)
    miktar = db.Column(db.Integer, nullable=False, default=1)
    toplam_fiyat = db.Column(db.Float, nullable=False)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)
    personel_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=True)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('kantin_satislari', lazy='dynamic'))
    personel = db.relationship('Personel', backref=db.backref('kantin_satislari', lazy='dynamic'))

    def __repr__(self):
        return f'<KantinSatis {self.id}>'
