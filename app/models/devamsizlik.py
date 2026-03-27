from datetime import datetime, date
from app.extensions import db


class Devamsizlik(db.Model):
    """Öğrenci devamsızlık kaydı (ders saati bazında)"""
    __tablename__ = 'devamsizlik_kayitlari'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    sube_id = db.Column(db.Integer, db.ForeignKey('subeler.id'), nullable=False)
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    ders_saati = db.Column(db.Integer, nullable=False)  # 1-8
    durum = db.Column(db.String(20), nullable=False, default='devamsiz')
    # devamsiz, gec, izinli, raporlu
    aciklama = db.Column(db.Text, nullable=True)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('devamsizliklar', lazy='dynamic'))
    sube = db.relationship('Sube', backref=db.backref('devamsizlik_kayitlari', lazy='dynamic'))
    olusturan = db.relationship('User', backref='devamsizlik_kayitlari')

    @property
    def durum_badge(self):
        durum_map = {
            'devamsiz': ('Devamsız', 'danger'),
            'gec': ('Geç Geldi', 'warning'),
            'izinli': ('İzinli', 'info'),
            'raporlu': ('Raporlu', 'secondary'),
        }
        return durum_map.get(self.durum, ('Bilinmiyor', 'secondary'))

    @property
    def ders_saati_str(self):
        return f"{self.ders_saati}. Ders"

    def __repr__(self):
        return f'<Devamsizlik {self.ogrenci_id} {self.tarih} {self.ders_saati}>'
