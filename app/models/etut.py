from datetime import datetime, date
from app.extensions import db


class Etut(db.Model):
    """Etut (Study Hall) tanimi"""
    __tablename__ = 'etutler'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(200), nullable=False)
    ders_id = db.Column(db.Integer, db.ForeignKey('dersler.id'), nullable=True)
    ogretmen_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    sube_id = db.Column(db.Integer, db.ForeignKey('subeler.id'), nullable=True)
    gun = db.Column(db.String(20), nullable=False)
    # Pazartesi, Sali, Carsamba, Persembe, Cuma
    baslangic_saati = db.Column(db.Time, nullable=False)
    bitis_saati = db.Column(db.Time, nullable=False)
    derslik = db.Column(db.String(50), nullable=True)
    kontenjan = db.Column(db.Integer, nullable=False, default=30)
    donem = db.Column(db.String(20), nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ders = db.relationship('Ders', backref=db.backref('etutler', lazy='dynamic'))
    ogretmen = db.relationship('Personel', backref=db.backref('etutler', lazy='dynamic'))
    sube = db.relationship('Sube', backref=db.backref('etutler', lazy='dynamic'))
    katilimlar = db.relationship('EtutKatilim', backref='etut', lazy='dynamic',
                                  cascade='all, delete-orphan')

    GUNLER = [
        ('Pazartesi', 'Pazartesi'),
        ('Sali', 'Sali'),
        ('Carsamba', 'Carsamba'),
        ('Persembe', 'Persembe'),
        ('Cuma', 'Cuma'),
    ]

    @property
    def gun_badge(self):
        badge_map = {
            'Pazartesi': 'primary',
            'Sali': 'info',
            'Carsamba': 'success',
            'Persembe': 'warning',
            'Cuma': 'danger',
        }
        return badge_map.get(self.gun, 'secondary')

    @property
    def saat_araligi(self):
        return f"{self.baslangic_saati.strftime('%H:%M')} - {self.bitis_saati.strftime('%H:%M')}"

    @property
    def katilimci_sayisi(self):
        """Benzersiz katilimci sayisi"""
        return db.session.query(
            db.func.count(db.func.distinct(EtutKatilim.ogrenci_id))
        ).filter(EtutKatilim.etut_id == self.id).scalar() or 0

    def __repr__(self):
        return f'<Etut {self.ad} {self.gun}>'


class EtutKatilim(db.Model):
    """Etut katilim kaydi"""
    __tablename__ = 'etut_katilimlari'

    id = db.Column(db.Integer, primary_key=True)
    etut_id = db.Column(db.Integer, db.ForeignKey('etutler.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    katildi = db.Column(db.Boolean, default=True)
    aciklama = db.Column(db.String(500), nullable=True)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('etut_katilimlari', lazy='dynamic'))

    def __repr__(self):
        return f'<EtutKatilim etut={self.etut_id} ogrenci={self.ogrenci_id} tarih={self.tarih}>'
