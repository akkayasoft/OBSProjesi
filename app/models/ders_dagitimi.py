from datetime import datetime
from app.extensions import db


class Ders(db.Model):
    """Ders tanımı"""
    __tablename__ = 'dersler'

    id = db.Column(db.Integer, primary_key=True)
    kod = db.Column(db.String(20), unique=True, nullable=False)  # MAT101
    ad = db.Column(db.String(100), nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    # Matematik, Fen, Sosyal, Dil, Sanat, Spor vb.
    haftalik_saat = db.Column(db.Integer, nullable=False, default=4)
    sinif_seviyesi = db.Column(db.Integer, nullable=False)  # 9, 10, 11, 12
    aciklama = db.Column(db.Text, nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    programlar = db.relationship('DersProgrami', backref='ders', lazy='dynamic')
    atamalar = db.relationship('OgretmenDersAtama', backref='ders', lazy='dynamic')

    @property
    def kategori_str(self):
        return self.kategori or '-'

    @property
    def sinif_seviyesi_str(self):
        return f"{self.sinif_seviyesi}. Sınıf"

    def __repr__(self):
        return f'<Ders {self.kod} {self.ad}>'


class DersProgrami(db.Model):
    """Haftalık ders programı"""
    __tablename__ = 'ders_programlari'

    id = db.Column(db.Integer, primary_key=True)
    ders_id = db.Column(db.Integer, db.ForeignKey('dersler.id'), nullable=False)
    ogretmen_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    sube_id = db.Column(db.Integer, db.ForeignKey('subeler.id'), nullable=False)
    gun = db.Column(db.String(20), nullable=False)
    # Pazartesi, Salı, Çarşamba, Perşembe, Cuma
    ders_saati = db.Column(db.Integer, nullable=False)  # 1-8
    donem = db.Column(db.String(20), nullable=False)  # 2025-2026
    derslik = db.Column(db.String(50), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('sube_id', 'gun', 'ders_saati', 'donem',
                            name='uq_sube_gun_saat_donem'),
    )

    ogretmen = db.relationship('Personel', backref=db.backref('ders_programlari', lazy='dynamic'))
    sube = db.relationship('Sube', backref=db.backref('ders_programlari', lazy='dynamic'))

    @property
    def gun_str(self):
        return self.gun

    @property
    def saat_str(self):
        return f"{self.ders_saati}. Ders"

    def __repr__(self):
        return f'<DersProgrami {self.gun} {self.ders_saati}. saat>'


class OgretmenDersAtama(db.Model):
    """Öğretmen-ders ataması"""
    __tablename__ = 'ogretmen_ders_atamalari'

    id = db.Column(db.Integer, primary_key=True)
    ogretmen_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    ders_id = db.Column(db.Integer, db.ForeignKey('dersler.id'), nullable=False)
    sube_id = db.Column(db.Integer, db.ForeignKey('subeler.id'), nullable=False)
    donem = db.Column(db.String(20), nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ogretmen = db.relationship('Personel', backref=db.backref('ders_atamalari', lazy='dynamic'))
    sube = db.relationship('Sube', backref=db.backref('ders_atamalari', lazy='dynamic'))

    def __repr__(self):
        return f'<OgretmenDersAtama {self.ogretmen_id} -> {self.ders_id}>'
