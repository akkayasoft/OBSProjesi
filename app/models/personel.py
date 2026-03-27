from datetime import datetime, date
from app.extensions import db


class PersonelIzin(db.Model):
    """Personel izin kaydı"""
    __tablename__ = 'personel_izinleri'

    id = db.Column(db.Integer, primary_key=True)
    personel_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    izin_turu = db.Column(db.String(20), nullable=False)
    # yillik, saglik, mazeret, ucretsiz, idari
    baslangic_tarihi = db.Column(db.Date, nullable=False)
    bitis_tarihi = db.Column(db.Date, nullable=False)
    gun_sayisi = db.Column(db.Integer, nullable=False)
    durum = db.Column(db.String(20), default='beklemede')
    # beklemede, onaylandi, reddedildi
    aciklama = db.Column(db.Text, nullable=True)
    onaylayan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    onaylayan = db.relationship('User', foreign_keys=[onaylayan_id], backref='onaylanan_izinler')
    olusturan = db.relationship('User', foreign_keys=[olusturan_id], backref='olusturulan_izinler')

    @property
    def izin_turu_str(self):
        turu_map = {
            'yillik': 'Yıllık İzin',
            'saglik': 'Sağlık İzni',
            'mazeret': 'Mazeret İzni',
            'ucretsiz': 'Ücretsiz İzin',
            'idari': 'İdari İzin',
        }
        return turu_map.get(self.izin_turu, self.izin_turu)

    @property
    def durum_badge(self):
        durum_map = {
            'beklemede': ('Beklemede', 'warning'),
            'onaylandi': ('Onaylandı', 'success'),
            'reddedildi': ('Reddedildi', 'danger'),
        }
        return durum_map.get(self.durum, ('Bilinmiyor', 'secondary'))

    def __repr__(self):
        return f'<PersonelIzin {self.personel_id} {self.izin_turu} {self.baslangic_tarihi}>'
