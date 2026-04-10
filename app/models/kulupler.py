from datetime import datetime, date
from app.extensions import db


class Kulup(db.Model):
    """Kulup (Club)"""
    __tablename__ = 'kulupler'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    kategori = db.Column(db.String(20), nullable=False, default='diger')
    # spor, sanat, bilim, sosyal, kultur, diger
    danisman_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=True)
    kontenjan = db.Column(db.Integer, default=30)
    toplanti_gunu = db.Column(db.String(20), nullable=True)
    toplanti_saati = db.Column(db.String(20), nullable=True)
    toplanti_yeri = db.Column(db.String(200), nullable=True)
    donem = db.Column(db.String(20), default='2025-2026')
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    danisman = db.relationship('Personel', backref=db.backref('danismanliklari', lazy='dynamic'))
    uyeler = db.relationship('KulupUyelik', backref='kulup', lazy='dynamic',
                             cascade='all, delete-orphan')
    etkinlikler = db.relationship('KulupEtkinlik', backref='kulup', lazy='dynamic',
                                  cascade='all, delete-orphan')

    @property
    def kategori_str(self):
        kategori_map = {
            'spor': 'Spor',
            'sanat': 'Sanat',
            'bilim': 'Bilim',
            'sosyal': 'Sosyal',
            'kultur': 'Kultur',
            'diger': 'Diger',
        }
        return kategori_map.get(self.kategori, self.kategori)

    @property
    def kategori_badge(self):
        badge_map = {
            'spor': 'success',
            'sanat': 'warning',
            'bilim': 'info',
            'sosyal': 'primary',
            'kultur': 'secondary',
            'diger': 'dark',
        }
        return badge_map.get(self.kategori, 'secondary')

    @property
    def kategori_icon(self):
        icon_map = {
            'spor': 'bi-trophy',
            'sanat': 'bi-palette',
            'bilim': 'bi-lightbulb',
            'sosyal': 'bi-people',
            'kultur': 'bi-book',
            'diger': 'bi-collection',
        }
        return icon_map.get(self.kategori, 'bi-collection')

    @property
    def aktif_uye_sayisi(self):
        return self.uyeler.filter_by(durum='aktif').count()

    def __repr__(self):
        return f'<Kulup {self.ad}>'


class KulupUyelik(db.Model):
    """Kulup Uyelik (Club Membership)"""
    __tablename__ = 'kulup_uyelikleri'

    id = db.Column(db.Integer, primary_key=True)
    kulup_id = db.Column(db.Integer, db.ForeignKey('kulupler.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    katilim_tarihi = db.Column(db.Date, default=date.today)
    gorev = db.Column(db.String(30), nullable=False, default='uye')
    # uye, baskan, baskan_yardimcisi, sekreter
    durum = db.Column(db.String(20), nullable=False, default='aktif')
    # aktif, pasif, ayrildi
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('kulup_id', 'ogrenci_id', name='uq_kulup_ogrenci'),
    )

    ogrenci = db.relationship('Ogrenci', backref=db.backref('kulup_uyelikleri', lazy='dynamic'))

    @property
    def gorev_str(self):
        gorev_map = {
            'uye': 'Uye',
            'baskan': 'Baskan',
            'baskan_yardimcisi': 'Baskan Yardimcisi',
            'sekreter': 'Sekreter',
        }
        return gorev_map.get(self.gorev, self.gorev)

    @property
    def gorev_badge(self):
        badge_map = {
            'uye': 'secondary',
            'baskan': 'danger',
            'baskan_yardimcisi': 'warning',
            'sekreter': 'info',
        }
        return badge_map.get(self.gorev, 'secondary')

    @property
    def durum_str(self):
        durum_map = {
            'aktif': 'Aktif',
            'pasif': 'Pasif',
            'ayrildi': 'Ayrildi',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        badge_map = {
            'aktif': 'success',
            'pasif': 'secondary',
            'ayrildi': 'danger',
        }
        return badge_map.get(self.durum, 'secondary')

    def __repr__(self):
        return f'<KulupUyelik kulup={self.kulup_id} ogrenci={self.ogrenci_id}>'


class KulupEtkinlik(db.Model):
    """Kulup Etkinlik (Club Activity/Event)"""
    __tablename__ = 'kulup_etkinlikleri'

    id = db.Column(db.Integer, primary_key=True)
    kulup_id = db.Column(db.Integer, db.ForeignKey('kulupler.id'), nullable=False)
    baslik = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    tarih = db.Column(db.DateTime, nullable=False)
    konum = db.Column(db.String(200), nullable=True)
    tur = db.Column(db.String(20), nullable=False, default='toplanti')
    # toplanti, yarisma, gosteri, gezi, diger
    durum = db.Column(db.String(20), nullable=False, default='planlandi')
    # planlandi, tamamlandi, iptal
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    olusturan = db.relationship('User', backref=db.backref('kulup_etkinlikleri', lazy='dynamic'))
    devamsizliklar = db.relationship('KulupDevamsizlik', backref='etkinlik', lazy='dynamic',
                                     cascade='all, delete-orphan')

    @property
    def tur_str(self):
        tur_map = {
            'toplanti': 'Toplanti',
            'yarisma': 'Yarisma',
            'gosteri': 'Gosteri',
            'gezi': 'Gezi',
            'diger': 'Diger',
        }
        return tur_map.get(self.tur, self.tur)

    @property
    def tur_badge(self):
        badge_map = {
            'toplanti': 'primary',
            'yarisma': 'success',
            'gosteri': 'warning',
            'gezi': 'info',
            'diger': 'secondary',
        }
        return badge_map.get(self.tur, 'secondary')

    @property
    def durum_str(self):
        durum_map = {
            'planlandi': 'Planlandi',
            'tamamlandi': 'Tamamlandi',
            'iptal': 'Iptal Edildi',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        badge_map = {
            'planlandi': 'info',
            'tamamlandi': 'success',
            'iptal': 'danger',
        }
        return badge_map.get(self.durum, 'secondary')

    def __repr__(self):
        return f'<KulupEtkinlik {self.baslik}>'


class KulupDevamsizlik(db.Model):
    """Kulup Devamsizlik (Club Attendance)"""
    __tablename__ = 'kulup_devamsizliklari'

    id = db.Column(db.Integer, primary_key=True)
    etkinlik_id = db.Column(db.Integer, db.ForeignKey('kulup_etkinlikleri.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    durum = db.Column(db.String(20), nullable=False, default='katilmadi')
    # katildi, katilmadi, izinli
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('etkinlik_id', 'ogrenci_id', name='uq_etkinlik_ogrenci'),
    )

    ogrenci = db.relationship('Ogrenci', backref=db.backref('kulup_devamsizliklari', lazy='dynamic'))

    @property
    def durum_str(self):
        durum_map = {
            'katildi': 'Katildi',
            'katilmadi': 'Katilmadi',
            'izinli': 'Izinli',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        badge_map = {
            'katildi': 'success',
            'katilmadi': 'danger',
            'izinli': 'warning',
        }
        return badge_map.get(self.durum, 'secondary')

    def __repr__(self):
        return f'<KulupDevamsizlik etkinlik={self.etkinlik_id} ogrenci={self.ogrenci_id}>'
