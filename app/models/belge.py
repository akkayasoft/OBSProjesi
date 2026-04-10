from datetime import datetime
from app.extensions import db


class Belge(db.Model):
    __tablename__ = 'belgeler'

    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(300), nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    dosya_adi = db.Column(db.String(300), nullable=True)
    dosya_yolu = db.Column(db.String(500), nullable=True)
    dosya_boyutu = db.Column(db.Integer, nullable=True)
    yukleyen_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    erisim = db.Column(db.String(20), nullable=False, default='herkes')
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    yukleyen = db.relationship('User', backref=db.backref('belgeler', lazy='dynamic'))

    KATEGORILER = [
        ('resmi', 'Resmi Yazi'), ('genelge', 'Genelge'), ('yonerge', 'Yonerge'),
        ('form', 'Form / Sablon'), ('rapor', 'Rapor'), ('diger', 'Diger'),
    ]

    ERISIM_TURLERI = [
        ('herkes', 'Herkes'), ('admin', 'Sadece Admin'),
        ('ogretmen', 'Ogretmenler'), ('personel', 'Personel'),
    ]

    @property
    def kategori_str(self):
        return dict(self.KATEGORILER).get(self.kategori, self.kategori)

    @property
    def boyut_str(self):
        if not self.dosya_boyutu:
            return '-'
        if self.dosya_boyutu < 1024:
            return f'{self.dosya_boyutu} B'
        elif self.dosya_boyutu < 1024 * 1024:
            return f'{self.dosya_boyutu / 1024:.1f} KB'
        return f'{self.dosya_boyutu / (1024 * 1024):.1f} MB'

    def __repr__(self):
        return f'<Belge {self.baslik}>'
