from datetime import datetime, date
from app.extensions import db


class Guzergah(db.Model):
    """Guzergah (Route)"""
    __tablename__ = 'servis_guzergahlar'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(200), nullable=False)
    kod = db.Column(db.String(20), unique=True, nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    baslangic_noktasi = db.Column(db.String(200), nullable=False)
    bitis_noktasi = db.Column(db.String(200), nullable=False)
    mesafe_km = db.Column(db.Float, nullable=True)
    tahmini_sure = db.Column(db.Integer, nullable=True)  # dakika
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    duraklar = db.relationship('ServisDurak', backref='guzergah', lazy='dynamic',
                               cascade='all, delete-orphan')
    araclar = db.relationship('Arac', backref='guzergah', lazy='dynamic')
    kayitlar = db.relationship('ServisKayit', backref='guzergah', lazy='dynamic')

    @property
    def durak_sayisi(self):
        return self.duraklar.count()

    @property
    def kayitli_ogrenci_sayisi(self):
        return self.kayitlar.filter_by(durum='aktif').count()

    def __repr__(self):
        return f'<Guzergah {self.kod} {self.ad}>'


class Arac(db.Model):
    """Arac (Vehicle)"""
    __tablename__ = 'servis_araclar'

    id = db.Column(db.Integer, primary_key=True)
    plaka = db.Column(db.String(20), unique=True, nullable=False)
    marka = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    kapasite = db.Column(db.Integer, nullable=False)
    sofor_adi = db.Column(db.String(200), nullable=False)
    sofor_telefon = db.Column(db.String(20), nullable=True)
    guzergah_id = db.Column(db.Integer, db.ForeignKey('servis_guzergahlar.id'), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Arac {self.plaka}>'


class ServisDurak(db.Model):
    """Servis Durak (Stop)"""
    __tablename__ = 'servis_duraklar'

    id = db.Column(db.Integer, primary_key=True)
    guzergah_id = db.Column(db.Integer, db.ForeignKey('servis_guzergahlar.id'), nullable=False)
    ad = db.Column(db.String(200), nullable=False)
    sira = db.Column(db.Integer, nullable=False)
    tahmini_varis = db.Column(db.String(10), nullable=True)  # "07:30"
    adres = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    kayitlar = db.relationship('ServisKayit', backref='durak', lazy='dynamic')

    def __repr__(self):
        return f'<ServisDurak {self.ad}>'


class ServisKayit(db.Model):
    """Servis Kayit (Student-Service Registration)"""
    __tablename__ = 'servis_kayitlar'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    guzergah_id = db.Column(db.Integer, db.ForeignKey('servis_guzergahlar.id'), nullable=False)
    durak_id = db.Column(db.Integer, db.ForeignKey('servis_duraklar.id'), nullable=True)
    binis_yonu = db.Column(db.String(20), nullable=False, default='her_ikisi')
    # gidis, donus, her_ikisi
    baslangic_tarihi = db.Column(db.Date, nullable=False, default=date.today)
    bitis_tarihi = db.Column(db.Date, nullable=True)
    ucret = db.Column(db.Float, nullable=True)
    durum = db.Column(db.String(20), nullable=False, default='aktif')
    # aktif, pasif, iptal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('ogrenci_id', 'guzergah_id', 'binis_yonu', name='uq_ogrenci_guzergah_yon'),
    )

    ogrenci = db.relationship('Ogrenci', backref=db.backref('servis_kayitlari', lazy='dynamic'))

    @property
    def binis_yonu_str(self):
        yon_map = {
            'gidis': 'Gidis',
            'donus': 'Donus',
            'her_ikisi': 'Gidis-Donus',
        }
        return yon_map.get(self.binis_yonu, self.binis_yonu)

    @property
    def binis_yonu_badge(self):
        badge_map = {
            'gidis': 'info',
            'donus': 'warning',
            'her_ikisi': 'primary',
        }
        return badge_map.get(self.binis_yonu, 'secondary')

    @property
    def durum_str(self):
        durum_map = {
            'aktif': 'Aktif',
            'pasif': 'Pasif',
            'iptal': 'Iptal',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        badge_map = {
            'aktif': 'success',
            'pasif': 'secondary',
            'iptal': 'danger',
        }
        return badge_map.get(self.durum, 'secondary')

    def __repr__(self):
        return f'<ServisKayit ogrenci={self.ogrenci_id} guzergah={self.guzergah_id}>'
