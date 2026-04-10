from datetime import datetime, date
from app.extensions import db


class Kitap(db.Model):
    __tablename__ = 'kitaplar'

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(20), nullable=True)
    baslik = db.Column(db.String(300), nullable=False)
    yazar = db.Column(db.String(200), nullable=False)
    yayinevi = db.Column(db.String(200), nullable=True)
    yayin_yili = db.Column(db.Integer, nullable=True)
    kategori = db.Column(db.String(100), nullable=False)
    raf_no = db.Column(db.String(50), nullable=True)
    adet = db.Column(db.Integer, default=1)
    mevcut_adet = db.Column(db.Integer, default=1)
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    odunc_kayitlari = db.relationship('KitapOdunc', backref='kitap', lazy='dynamic',
                                       cascade='all, delete-orphan')

    KATEGORILER = [
        ('roman', 'Roman'), ('hikaye', 'Hikaye'), ('siir', 'Siir'),
        ('bilim', 'Bilim'), ('tarih', 'Tarih'), ('ders_kitabi', 'Ders Kitabi'),
        ('ansiklopedi', 'Ansiklopedi'), ('diger', 'Diger'),
    ]

    @property
    def musait(self):
        return self.mevcut_adet > 0

    def __repr__(self):
        return f'<Kitap {self.baslik}>'


class KitapOdunc(db.Model):
    __tablename__ = 'kitap_odunc'

    id = db.Column(db.Integer, primary_key=True)
    kitap_id = db.Column(db.Integer, db.ForeignKey('kitaplar.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=True)
    personel_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=True)
    odunc_tarihi = db.Column(db.Date, nullable=False, default=date.today)
    iade_tarihi = db.Column(db.Date, nullable=True)
    son_iade_tarihi = db.Column(db.Date, nullable=False)
    durum = db.Column(db.String(20), nullable=False, default='odunc')
    aciklama = db.Column(db.Text, nullable=True)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('odunc_kitaplar', lazy='dynamic'))
    personel = db.relationship('Personel', backref=db.backref('odunc_kitaplar', lazy='dynamic'))

    @property
    def gecikti_mi(self):
        if self.durum == 'odunc' and date.today() > self.son_iade_tarihi:
            return True
        return False

    @property
    def alan_kisi(self):
        if self.ogrenci:
            return self.ogrenci.tam_ad
        elif self.personel:
            return f"{self.personel.ad} {self.personel.soyad}"
        return '-'

    @property
    def durum_str(self):
        d = {'odunc': 'Odunc', 'iade_edildi': 'Iade Edildi', 'gecikti': 'Gecikti'}
        return d.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        d = {'odunc': 'warning', 'iade_edildi': 'success', 'gecikti': 'danger'}
        return d.get(self.durum, 'secondary')

    def __repr__(self):
        return f'<KitapOdunc {self.kitap_id} -> {self.alan_kisi}>'
