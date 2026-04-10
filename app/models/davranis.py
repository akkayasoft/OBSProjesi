from datetime import datetime, date
from app.extensions import db


class DavranisKurali(db.Model):
    """Davranis Kurali (Behavior Rule)"""
    __tablename__ = 'davranis_kurallari'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(200), nullable=False)
    kategori = db.Column(db.String(50), nullable=False, default='diger')
    # akademik, sosyal, disiplin, saglik, diger
    tur = db.Column(db.String(20), nullable=False, default='olumlu')
    # olumlu, olumsuz
    varsayilan_puan = db.Column(db.Integer, nullable=False, default=0)
    aciklama = db.Column(db.Text, nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    kayitlar = db.relationship('DavranisDeğerlendirme', backref='kural', lazy='dynamic')

    @property
    def tur_str(self):
        return {'olumlu': 'Olumlu', 'olumsuz': 'Olumsuz'}.get(self.tur, self.tur)

    @property
    def tur_badge(self):
        return {'olumlu': 'success', 'olumsuz': 'danger'}.get(self.tur, 'secondary')

    @property
    def kategori_str(self):
        kategori_map = {
            'akademik': 'Akademik',
            'sosyal': 'Sosyal',
            'disiplin': 'Disiplin',
            'saglik': 'Saglik',
            'diger': 'Diger',
        }
        return kategori_map.get(self.kategori, self.kategori)

    @property
    def kategori_badge(self):
        badge_map = {
            'akademik': 'primary',
            'sosyal': 'info',
            'disiplin': 'danger',
            'saglik': 'warning',
            'diger': 'secondary',
        }
        return badge_map.get(self.kategori, 'secondary')

    def __repr__(self):
        return f'<DavranisKurali {self.ad}>'


class DavranisDeğerlendirme(db.Model):
    """Davranis Degerlendirme Kaydi (Behavior Assessment Record)"""
    __tablename__ = 'davranis_degerlendirmeleri'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    ogretmen_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    sinif_id = db.Column(db.Integer, db.ForeignKey('siniflar.id'), nullable=True)
    kural_id = db.Column(db.Integer, db.ForeignKey('davranis_kurallari.id'), nullable=True)
    tur = db.Column(db.String(20), nullable=False, default='olumlu')
    # olumlu, olumsuz
    kategori = db.Column(db.String(50), nullable=False, default='diger')
    # akademik, sosyal, disiplin, saglik, diger
    aciklama = db.Column(db.Text, nullable=False)
    puan = db.Column(db.Integer, nullable=False, default=0)
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('davranis_degerlendirmeleri', lazy='dynamic'))
    ogretmen = db.relationship('Personel', backref=db.backref('davranis_degerlendirmeleri', lazy='dynamic'))
    sinif = db.relationship('Sinif', backref=db.backref('davranis_degerlendirmeleri', lazy='dynamic'))

    @property
    def tur_str(self):
        return {'olumlu': 'Olumlu', 'olumsuz': 'Olumsuz'}.get(self.tur, self.tur)

    @property
    def tur_badge(self):
        return {'olumlu': 'success', 'olumsuz': 'danger'}.get(self.tur, 'secondary')

    @property
    def kategori_str(self):
        kategori_map = {
            'akademik': 'Akademik',
            'sosyal': 'Sosyal',
            'disiplin': 'Disiplin',
            'saglik': 'Saglik',
            'diger': 'Diger',
        }
        return kategori_map.get(self.kategori, self.kategori)

    @property
    def kategori_badge(self):
        badge_map = {
            'akademik': 'primary',
            'sosyal': 'info',
            'disiplin': 'danger',
            'saglik': 'warning',
            'diger': 'secondary',
        }
        return badge_map.get(self.kategori, 'secondary')

    def __repr__(self):
        return f'<DavranisDeğerlendirme {self.tur} {self.kategori}>'
