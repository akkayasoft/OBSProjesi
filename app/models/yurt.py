from datetime import datetime, date
from app.extensions import db


class YurtOda(db.Model):
    __tablename__ = 'yurt_odalar'

    id = db.Column(db.Integer, primary_key=True)
    oda_no = db.Column(db.String(20), nullable=False)
    bina = db.Column(db.String(100), nullable=True)
    kat = db.Column(db.Integer, nullable=False)
    kapasite = db.Column(db.Integer, nullable=False)
    cinsiyet = db.Column(db.String(10), nullable=False, default='karma')
    durum = db.Column(db.String(20), nullable=False, default='aktif')
    aciklama = db.Column(db.Text, nullable=True)

    kayitlar = db.relationship('YurtKayit', backref='oda', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def dolu_yatak(self):
        return self.kayitlar.filter_by(aktif=True).count()

    @property
    def bos_yatak(self):
        return max(0, self.kapasite - self.dolu_yatak)

    @property
    def durum_badge(self):
        return {'aktif': 'success', 'bakim': 'warning', 'kapali': 'danger'}.get(self.durum, 'secondary')

    def __repr__(self):
        return f'<YurtOda {self.oda_no}>'


class YurtKayit(db.Model):
    __tablename__ = 'yurt_kayitlar'

    id = db.Column(db.Integer, primary_key=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('yurt_odalar.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    baslangic_tarihi = db.Column(db.Date, nullable=False, default=date.today)
    bitis_tarihi = db.Column(db.Date, nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    yatak_no = db.Column(db.String(10), nullable=True)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('yurt_kayitlari', lazy='dynamic'))

    def __repr__(self):
        return f'<YurtKayit oda={self.oda_id} ogrenci={self.ogrenci_id}>'


class YurtYoklama(db.Model):
    __tablename__ = 'yurt_yoklamalar'

    id = db.Column(db.Integer, primary_key=True)
    oda_id = db.Column(db.Integer, db.ForeignKey('yurt_odalar.id'), nullable=False)
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    yoklama_turu = db.Column(db.String(10), nullable=False)  # sabah / aksam
    yapan_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    oda = db.relationship('YurtOda', backref=db.backref('yoklamalar', lazy='dynamic'))
    yapan = db.relationship('Personel', backref=db.backref('yurt_yoklamalari', lazy='dynamic'))
    detaylar = db.relationship('YurtYoklamaDetay', backref='yoklama', lazy='dynamic',
                                cascade='all, delete-orphan')

    def __repr__(self):
        return f'<YurtYoklama {self.tarih} {self.yoklama_turu}>'


class YurtYoklamaDetay(db.Model):
    __tablename__ = 'yurt_yoklama_detay'

    id = db.Column(db.Integer, primary_key=True)
    yoklama_id = db.Column(db.Integer, db.ForeignKey('yurt_yoklamalar.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    durum = db.Column(db.String(10), nullable=False, default='mevcut')  # mevcut/izinli/yok

    ogrenci = db.relationship('Ogrenci')

    @property
    def durum_badge(self):
        return {'mevcut': 'success', 'izinli': 'info', 'yok': 'danger'}.get(self.durum, 'secondary')

    @property
    def durum_str(self):
        return {'mevcut': 'Mevcut', 'izinli': 'Izinli', 'yok': 'Yok'}.get(self.durum, self.durum)
