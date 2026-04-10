from datetime import datetime, date
from app.extensions import db


class SinavTuru(db.Model):
    """Sınav türü tanımı (Yazılı, Sözlü, Performans, Proje)"""
    __tablename__ = 'sinav_turleri'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(50), nullable=False)  # "1. Yazılı", "Sözlü" vb.
    tur = db.Column(db.String(20), nullable=False)  # yazili, sozlu, performans, proje
    agirlik = db.Column(db.Float, default=1.0)  # Ağırlık yüzdesi
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sinavlar = db.relationship('Sinav', backref='sinav_turu', lazy='dynamic')

    @property
    def tur_str(self):
        tur_map = {
            'yazili': 'Yazılı',
            'sozlu': 'Sözlü',
            'performans': 'Performans',
            'proje': 'Proje',
        }
        return tur_map.get(self.tur, self.tur)

    def __repr__(self):
        return f'<SinavTuru {self.ad}>'


class Sinav(db.Model):
    """Sınav tanımı"""
    __tablename__ = 'sinavlar'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(200), nullable=False)
    sinav_turu_id = db.Column(db.Integer, db.ForeignKey('sinav_turleri.id'), nullable=False)
    ders_id = db.Column(db.Integer, db.ForeignKey('dersler.id'), nullable=False)
    sube_id = db.Column(db.Integer, db.ForeignKey('subeler.id'), nullable=False)
    ogretmen_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    tarih = db.Column(db.Date, nullable=False)
    donem = db.Column(db.String(20), nullable=False, default='2025-2026')
    aciklama = db.Column(db.Text, nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ders = db.relationship('Ders', backref=db.backref('sinavlar', lazy='dynamic'))
    sube = db.relationship('Sube', backref=db.backref('sinavlar', lazy='dynamic'))
    ogretmen = db.relationship('Personel', backref=db.backref('sinavlar', lazy='dynamic'))
    notlar = db.relationship('OgrenciNot', backref='sinav', lazy='dynamic',
                             cascade='all, delete-orphan')

    @property
    def not_ortalamasi(self):
        notlar = self.notlar.filter(OgrenciNot.puan.isnot(None)).all()
        if not notlar:
            return 0
        return round(sum(n.puan for n in notlar) / len(notlar), 2)

    @property
    def not_girilen_sayi(self):
        return self.notlar.filter(OgrenciNot.puan.isnot(None)).count()

    def __repr__(self):
        return f'<Sinav {self.ad}>'


class OgrenciNot(db.Model):
    """Öğrenci notu"""
    __tablename__ = 'ogrenci_notlari'

    id = db.Column(db.Integer, primary_key=True)
    sinav_id = db.Column(db.Integer, db.ForeignKey('sinavlar.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    puan = db.Column(db.Float, nullable=True)
    harf_notu = db.Column(db.String(5), nullable=True)
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('sinav_id', 'ogrenci_id', name='uq_sinav_ogrenci'),
    )

    ogrenci = db.relationship('Ogrenci', backref=db.backref('notlar', lazy='dynamic'))

    def hesapla_harf_notu(self):
        """Puana göre harf notu hesapla"""
        if self.puan is None:
            self.harf_notu = None
            return
        p = self.puan
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
        return f'<OgrenciNot sinav={self.sinav_id} ogrenci={self.ogrenci_id} puan={self.puan}>'


class OdevTakip(db.Model):
    """Ödev takip"""
    __tablename__ = 'odev_takip'

    id = db.Column(db.Integer, primary_key=True)
    ders_id = db.Column(db.Integer, db.ForeignKey('dersler.id'), nullable=False)
    sube_id = db.Column(db.Integer, db.ForeignKey('subeler.id'), nullable=False)
    ogretmen_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    baslik = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    son_teslim_tarihi = db.Column(db.Date, nullable=False)
    donem = db.Column(db.String(20), nullable=False, default='2025-2026')
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ders = db.relationship('Ders', backref=db.backref('odevler', lazy='dynamic'))
    sube = db.relationship('Sube', backref=db.backref('odevler', lazy='dynamic'))
    ogretmen = db.relationship('Personel', backref=db.backref('odevler', lazy='dynamic'))
    teslimler = db.relationship('OdevTeslim', backref='odev', lazy='dynamic',
                                cascade='all, delete-orphan')

    @property
    def teslim_orani(self):
        toplam = self.teslimler.count()
        if toplam == 0:
            return 0
        teslim_edilen = self.teslimler.filter(
            OdevTeslim.durum == 'teslim_edildi'
        ).count()
        return round(teslim_edilen / toplam * 100, 1)

    @property
    def gecikti_mi(self):
        return date.today() > self.son_teslim_tarihi

    def __repr__(self):
        return f'<OdevTakip {self.baslik}>'


class OdevTeslim(db.Model):
    """Ödev teslim durumu"""
    __tablename__ = 'odev_teslimleri'

    id = db.Column(db.Integer, primary_key=True)
    odev_id = db.Column(db.Integer, db.ForeignKey('odev_takip.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    teslim_tarihi = db.Column(db.Date, nullable=True)
    durum = db.Column(db.String(20), nullable=False, default='teslim_edilmedi')
    # teslim_edildi, teslim_edilmedi, gecikti
    puan = db.Column(db.Float, nullable=True)
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('odev_teslimleri', lazy='dynamic'))

    def __repr__(self):
        return f'<OdevTeslim odev={self.odev_id} ogrenci={self.ogrenci_id} durum={self.durum}>'
