from datetime import datetime
from app.extensions import db


class DenetimLog(db.Model):
    __tablename__ = 'denetim_loglari'

    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    islem = db.Column(db.String(50), nullable=False)  # giris/cikis/ekleme/guncelleme/silme/goruntuleme
    modul = db.Column(db.String(100), nullable=False)
    detay = db.Column(db.Text, nullable=True)
    ip_adresi = db.Column(db.String(50), nullable=True)
    tarih = db.Column(db.DateTime, default=datetime.utcnow)

    kullanici = db.relationship('User', backref=db.backref('denetim_loglari', lazy='dynamic'))

    ISLEM_TIPLERI = [
        ('giris', 'Giris'), ('cikis', 'Cikis'),
        ('ekleme', 'Ekleme'), ('guncelleme', 'Guncelleme'),
        ('silme', 'Silme'), ('goruntuleme', 'Goruntuleme'),
    ]

    @property
    def islem_badge(self):
        return {
            'giris': 'success', 'cikis': 'secondary', 'ekleme': 'primary',
            'guncelleme': 'warning', 'silme': 'danger', 'goruntuleme': 'info',
        }.get(self.islem, 'secondary')

    @property
    def islem_str(self):
        return dict(self.ISLEM_TIPLERI).get(self.islem, self.islem)

    def __repr__(self):
        return f'<DenetimLog {self.islem} {self.modul}>'
