from datetime import datetime
from app.extensions import db


class Duyuru(db.Model):
    """Duyuru (Announcement)"""
    __tablename__ = 'duyurular'

    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    icerik = db.Column(db.Text, nullable=False)
    kategori = db.Column(db.String(20), nullable=False, default='genel')
    # genel, akademik, idari, etkinlik, acil
    oncelik = db.Column(db.String(20), nullable=False, default='normal')
    # normal, onemli, acil
    hedef_kitle = db.Column(db.String(20), nullable=False, default='tumu')
    # tumu, ogretmenler, ogrenciler, veliler, personel
    yayinlayan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    yayinlanma_tarihi = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    bitis_tarihi = db.Column(db.DateTime, nullable=True)
    sabitlenmis = db.Column(db.Boolean, default=False)
    aktif = db.Column(db.Boolean, default=True)
    okunma_sayisi = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    yayinlayan = db.relationship('User', backref=db.backref('duyurular', lazy='dynamic'))
    okunmalar = db.relationship('DuyuruOkunma', backref='duyuru', lazy='dynamic',
                                cascade='all, delete-orphan')

    @property
    def kategori_str(self):
        kategori_map = {
            'genel': 'Genel',
            'akademik': 'Akademik',
            'idari': 'İdari',
            'etkinlik': 'Etkinlik',
            'acil': 'Acil',
        }
        return kategori_map.get(self.kategori, self.kategori)

    @property
    def kategori_renk(self):
        renk_map = {
            'genel': '#6c757d',
            'akademik': '#0d6efd',
            'idari': '#198754',
            'etkinlik': '#ffc107',
            'acil': '#dc3545',
        }
        return renk_map.get(self.kategori, '#6c757d')

    @property
    def kategori_badge(self):
        badge_map = {
            'genel': 'secondary',
            'akademik': 'primary',
            'idari': 'success',
            'etkinlik': 'warning',
            'acil': 'danger',
        }
        return badge_map.get(self.kategori, 'secondary')

    @property
    def oncelik_str(self):
        oncelik_map = {
            'normal': 'Normal',
            'onemli': 'Önemli',
            'acil': 'Acil',
        }
        return oncelik_map.get(self.oncelik, self.oncelik)

    @property
    def oncelik_badge(self):
        badge_map = {
            'normal': 'secondary',
            'onemli': 'warning',
            'acil': 'danger',
        }
        return badge_map.get(self.oncelik, 'secondary')

    @property
    def hedef_kitle_str(self):
        hedef_map = {
            'tumu': 'Tümü',
            'ogretmenler': 'Öğretmenler',
            'ogrenciler': 'Öğrenciler',
            'veliler': 'Veliler',
            'personel': 'Personel',
        }
        return hedef_map.get(self.hedef_kitle, self.hedef_kitle)

    @property
    def suresi_doldu(self):
        if self.bitis_tarihi:
            return datetime.utcnow() > self.bitis_tarihi
        return False

    def kullanici_okudu_mu(self, user_id):
        return self.okunmalar.filter_by(kullanici_id=user_id).first() is not None

    def __repr__(self):
        return f'<Duyuru {self.baslik}>'


class DuyuruOkunma(db.Model):
    """Duyuru okunma takibi"""
    __tablename__ = 'duyuru_okunmalari'

    id = db.Column(db.Integer, primary_key=True)
    duyuru_id = db.Column(db.Integer, db.ForeignKey('duyurular.id'), nullable=False)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    okunma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('duyuru_id', 'kullanici_id', name='uq_duyuru_kullanici'),
    )

    kullanici = db.relationship('User', backref=db.backref('okunan_duyurular', lazy='dynamic'))

    def __repr__(self):
        return f'<DuyuruOkunma duyuru={self.duyuru_id} kullanici={self.kullanici_id}>'


class Etkinlik(db.Model):
    """Etkinlik / Takvim"""
    __tablename__ = 'etkinlikler'

    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    tur = db.Column(db.String(20), nullable=False, default='diger')
    # toplanti, sinav, kutlama, gezi, spor, diger
    baslangic_tarihi = db.Column(db.DateTime, nullable=False)
    bitis_tarihi = db.Column(db.DateTime, nullable=False)
    konum = db.Column(db.String(200), nullable=True)
    renk = db.Column(db.String(10), nullable=False, default='#3498db')
    tum_gun = db.Column(db.Boolean, default=False)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    olusturan = db.relationship('User', backref=db.backref('etkinlikler', lazy='dynamic'))

    @property
    def tur_str(self):
        tur_map = {
            'toplanti': 'Toplantı',
            'sinav': 'Sınav',
            'kutlama': 'Kutlama',
            'gezi': 'Gezi',
            'spor': 'Spor',
            'diger': 'Diğer',
        }
        return tur_map.get(self.tur, self.tur)

    @property
    def tur_icon(self):
        icon_map = {
            'toplanti': 'bi-people',
            'sinav': 'bi-pencil-square',
            'kutlama': 'bi-balloon',
            'gezi': 'bi-bus-front',
            'spor': 'bi-trophy',
            'diger': 'bi-calendar-event',
        }
        return icon_map.get(self.tur, 'bi-calendar-event')

    def __repr__(self):
        return f'<Etkinlik {self.baslik}>'


class Hatirlatma(db.Model):
    """Hatırlatma"""
    __tablename__ = 'hatirlatmalar'

    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    tarih = db.Column(db.DateTime, nullable=False)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tamamlandi = db.Column(db.Boolean, default=False)
    oncelik = db.Column(db.String(20), nullable=False, default='normal')
    # dusuk, normal, yuksek
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    kullanici = db.relationship('User', backref=db.backref('hatirlatmalar', lazy='dynamic'))

    @property
    def oncelik_str(self):
        oncelik_map = {
            'dusuk': 'Düşük',
            'normal': 'Normal',
            'yuksek': 'Yüksek',
        }
        return oncelik_map.get(self.oncelik, self.oncelik)

    @property
    def oncelik_badge(self):
        badge_map = {
            'dusuk': 'info',
            'normal': 'secondary',
            'yuksek': 'danger',
        }
        return badge_map.get(self.oncelik, 'secondary')

    def __repr__(self):
        return f'<Hatirlatma {self.baslik}>'
