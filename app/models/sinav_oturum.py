from datetime import datetime, date
from app.extensions import db


class SinavOturum(db.Model):
    """Sinav Oturumu"""
    __tablename__ = 'sinav_oturumlari'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(200), nullable=False)
    sinav_turu = db.Column(db.String(20), nullable=False, default='yazili')
    # yazili, sozlu, test, performans
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    baslangic_saati = db.Column(db.Time, nullable=False)
    bitis_saati = db.Column(db.Time, nullable=False)
    sinif_id = db.Column(db.Integer, db.ForeignKey('siniflar.id'), nullable=False)
    ders_id = db.Column(db.Integer, db.ForeignKey('dersler.id'), nullable=False)
    ogretmen_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    derslik = db.Column(db.String(100), nullable=True)
    durum = db.Column(db.String(20), nullable=False, default='planlanmis')
    # planlanmis, devam_ediyor, tamamlandi, iptal
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sinif = db.relationship('Sinif', backref=db.backref('sinav_oturumlari', lazy='dynamic'))
    ders = db.relationship('Ders', backref=db.backref('sinav_oturumlari', lazy='dynamic'))
    ogretmen = db.relationship('Personel', backref=db.backref('sinav_oturumlari', lazy='dynamic'),
                               foreign_keys=[ogretmen_id])
    gozetmenler = db.relationship('SinavGozetmen', backref='sinav_oturum',
                                  lazy='dynamic', cascade='all, delete-orphan')

    @property
    def sinav_turu_str(self):
        turu_map = {
            'yazili': 'Yazili',
            'sozlu': 'Sozlu',
            'test': 'Test',
            'performans': 'Performans',
        }
        return turu_map.get(self.sinav_turu, self.sinav_turu)

    @property
    def sinav_turu_badge(self):
        badge_map = {
            'yazili': 'primary',
            'sozlu': 'info',
            'test': 'warning',
            'performans': 'success',
        }
        return badge_map.get(self.sinav_turu, 'secondary')

    @property
    def durum_str(self):
        durum_map = {
            'planlanmis': 'Planlanmis',
            'devam_ediyor': 'Devam Ediyor',
            'tamamlandi': 'Tamamlandi',
            'iptal': 'Iptal',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        badge_map = {
            'planlanmis': 'secondary',
            'devam_ediyor': 'warning',
            'tamamlandi': 'success',
            'iptal': 'danger',
        }
        return badge_map.get(self.durum, 'secondary')

    def __repr__(self):
        return f'<SinavOturum {self.ad}>'


class SinavGozetmen(db.Model):
    """Sinav Gozetmeni"""
    __tablename__ = 'sinav_gozetmenleri'

    id = db.Column(db.Integer, primary_key=True)
    sinav_oturum_id = db.Column(db.Integer, db.ForeignKey('sinav_oturumlari.id'), nullable=False)
    ogretmen_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    gorev = db.Column(db.String(20), nullable=False, default='gozetmen')
    # basgozetmen, gozetmen

    ogretmen = db.relationship('Personel', backref=db.backref('sinav_gozetmenlikleri', lazy='dynamic'))

    @property
    def gorev_str(self):
        return {'basgozetmen': 'Bas Gozetmen', 'gozetmen': 'Gozetmen'}.get(self.gorev, self.gorev)

    @property
    def gorev_badge(self):
        return {'basgozetmen': 'primary', 'gozetmen': 'secondary'}.get(self.gorev, 'secondary')

    def __repr__(self):
        return f'<SinavGozetmen {self.ogretmen_id} - {self.gorev}>'
