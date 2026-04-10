from datetime import datetime
from app.extensions import db


class Karne(db.Model):
    """Karne / Report Card"""
    __tablename__ = 'karneler'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    donem = db.Column(db.String(20), nullable=False)  # "1. Donem", "2. Donem"
    ogretim_yili = db.Column(db.String(20), nullable=False)  # "2025-2026"
    sinif_id = db.Column(db.Integer, db.ForeignKey('siniflar.id'), nullable=False)
    genel_ortalama = db.Column(db.Float, nullable=True)
    davranis_notu = db.Column(db.String(50), nullable=True)
    devamsizlik_ozetsiz = db.Column(db.Integer, default=0)
    devamsizlik_ozetli = db.Column(db.Integer, default=0)
    sinif_ogretmeni_notu = db.Column(db.Text, nullable=True)
    mudur_notu = db.Column(db.Text, nullable=True)
    durum = db.Column(db.String(20), default='taslak')  # taslak, onaylandi, basildi
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('karneler', lazy='dynamic'))
    sinif = db.relationship('Sinif', backref=db.backref('karneler', lazy='dynamic'))
    ders_notlari = db.relationship('KarneDersNotu', backref='karne', lazy='dynamic',
                                   cascade='all, delete-orphan')

    @property
    def durum_str(self):
        durum_map = {
            'taslak': 'Taslak',
            'onaylandi': 'Onaylandi',
            'basildi': 'Basildi',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        badge_map = {
            'taslak': 'secondary',
            'onaylandi': 'success',
            'basildi': 'primary',
        }
        return badge_map.get(self.durum, 'secondary')

    @property
    def toplam_devamsizlik(self):
        return (self.devamsizlik_ozetsiz or 0) + (self.devamsizlik_ozetli or 0)

    def hesapla_genel_ortalama(self):
        """Ders notlarindan genel ortalama hesapla"""
        notlar = self.ders_notlari.filter(KarneDersNotu.yilsonu.isnot(None)).all()
        if not notlar:
            self.genel_ortalama = None
            return
        self.genel_ortalama = round(
            sum(n.yilsonu for n in notlar) / len(notlar), 2
        )

    def __repr__(self):
        return f'<Karne {self.ogrenci_id} {self.donem} {self.ogretim_yili}>'


class KarneDersNotu(db.Model):
    """Karne ders notu detayi"""
    __tablename__ = 'karne_ders_notlari'

    id = db.Column(db.Integer, primary_key=True)
    karne_id = db.Column(db.Integer, db.ForeignKey('karneler.id'), nullable=False)
    ders_adi = db.Column(db.String(200), nullable=False)
    ders_kodu = db.Column(db.String(50), nullable=True)
    sinav1 = db.Column(db.Float, nullable=True)
    sinav2 = db.Column(db.Float, nullable=True)
    sinav3 = db.Column(db.Float, nullable=True)
    ortalama = db.Column(db.Float, nullable=True)
    performans = db.Column(db.Float, nullable=True)
    proje = db.Column(db.Float, nullable=True)
    yilsonu = db.Column(db.Float, nullable=True)
    harf_notu = db.Column(db.String(5), nullable=True)

    def hesapla_harf_notu(self):
        """Yilsonu notuna gore harf notu hesapla"""
        if self.yilsonu is None:
            self.harf_notu = None
            return
        p = self.yilsonu
        if p >= 90:
            self.harf_notu = 'AA'
        elif p >= 85:
            self.harf_notu = 'BA'
        elif p >= 80:
            self.harf_notu = 'BB'
        elif p >= 75:
            self.harf_notu = 'CB'
        elif p >= 70:
            self.harf_notu = 'CC'
        elif p >= 65:
            self.harf_notu = 'DC'
        elif p >= 60:
            self.harf_notu = 'DD'
        elif p >= 50:
            self.harf_notu = 'FD'
        else:
            self.harf_notu = 'FF'

    def __repr__(self):
        return f'<KarneDersNotu {self.ders_adi} yilsonu={self.yilsonu}>'
