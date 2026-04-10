from datetime import datetime, date
from app.extensions import db


class OrtakSinav(db.Model):
    """Ortak Sinav (Common Exam)"""
    __tablename__ = 'ortak_sinavlar'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(200), nullable=False)
    ders_id = db.Column(db.Integer, db.ForeignKey('dersler.id'), nullable=False)
    seviye = db.Column(db.Integer, nullable=False)  # sinif seviyesi: 9, 10, 11, 12
    donem = db.Column(db.String(20), nullable=False)  # 2025-2026
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    sure_dakika = db.Column(db.Integer, nullable=False, default=40)
    soru_sayisi = db.Column(db.Integer, nullable=False, default=20)
    toplam_puan = db.Column(db.Float, nullable=False, default=100.0)
    durum = db.Column(db.String(20), nullable=False, default='hazirlaniyor')
    # hazirlaniyor, uygulanmis, degerlendirme, tamamlandi
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ders = db.relationship('Ders', backref=db.backref('ortak_sinavlar', lazy='dynamic'))
    sonuclar = db.relationship('OrtakSinavSonuc', backref='sinav', lazy='dynamic',
                               cascade='all, delete-orphan')

    @property
    def durum_str(self):
        durum_map = {
            'hazirlaniyor': 'Hazirlaniyor',
            'uygulanmis': 'Uygulanmis',
            'degerlendirme': 'Degerlendirme',
            'tamamlandi': 'Tamamlandi',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        badge_map = {
            'hazirlaniyor': 'warning',
            'uygulanmis': 'info',
            'degerlendirme': 'primary',
            'tamamlandi': 'success',
        }
        return badge_map.get(self.durum, 'secondary')

    @property
    def seviye_str(self):
        return f"{self.seviye}. Sinif"

    @property
    def sonuc_sayisi(self):
        return self.sonuclar.count()

    @property
    def ortalama_puan(self):
        from sqlalchemy import func
        result = db.session.query(func.avg(OrtakSinavSonuc.puan)).filter(
            OrtakSinavSonuc.ortak_sinav_id == self.id
        ).scalar()
        return round(result, 2) if result else 0

    def __repr__(self):
        return f'<OrtakSinav {self.ad}>'


class OrtakSinavSonuc(db.Model):
    """Ortak Sinav Sonucu"""
    __tablename__ = 'ortak_sinav_sonuclari'

    id = db.Column(db.Integer, primary_key=True)
    ortak_sinav_id = db.Column(db.Integer, db.ForeignKey('ortak_sinavlar.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    sube_id = db.Column(db.Integer, db.ForeignKey('subeler.id'), nullable=False)
    puan = db.Column(db.Float, nullable=False, default=0)
    dogru_sayisi = db.Column(db.Integer, nullable=True)
    yanlis_sayisi = db.Column(db.Integer, nullable=True)
    bos_sayisi = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('ortak_sinav_sonuclari', lazy='dynamic'))
    sube = db.relationship('Sube', backref=db.backref('ortak_sinav_sonuclari', lazy='dynamic'))

    def __repr__(self):
        return f'<OrtakSinavSonuc sinav={self.ortak_sinav_id} ogrenci={self.ogrenci_id}>'
