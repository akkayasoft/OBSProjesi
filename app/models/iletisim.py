from datetime import datetime
from app.extensions import db


class Mesaj(db.Model):
    """Dahili Mesaj (Internal Message)"""
    __tablename__ = 'mesajlar'

    id = db.Column(db.Integer, primary_key=True)
    gonderen_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alici_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    konu = db.Column(db.String(200), nullable=False)
    icerik = db.Column(db.Text, nullable=False)
    okundu = db.Column(db.Boolean, default=False)
    okunma_tarihi = db.Column(db.DateTime, nullable=True)
    onemli = db.Column(db.Boolean, default=False)
    silindi_gonderen = db.Column(db.Boolean, default=False)
    silindi_alici = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    gonderen = db.relationship('User', foreign_keys=[gonderen_id],
                               backref=db.backref('gonderilen_mesajlar', lazy='dynamic'))
    alici = db.relationship('User', foreign_keys=[alici_id],
                            backref=db.backref('alinan_mesajlar', lazy='dynamic'))

    def __repr__(self):
        return f'<Mesaj {self.konu}>'


class TopluMesaj(db.Model):
    """Toplu Mesaj / SMS"""
    __tablename__ = 'toplu_mesajlar'

    id = db.Column(db.Integer, primary_key=True)
    gonderen_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    baslik = db.Column(db.String(200), nullable=False)
    icerik = db.Column(db.Text, nullable=False)
    hedef_grup = db.Column(db.String(20), nullable=False, default='tumu')
    # tumu, ogretmenler, veliler, personel, sinif
    hedef_sinif = db.Column(db.String(20), nullable=True)
    gonderim_tarihi = db.Column(db.DateTime, nullable=True)
    gonderim_turu = db.Column(db.String(20), nullable=False, default='sistem')
    # sistem, sms, email
    toplam_alici = db.Column(db.Integer, default=0)
    basarili_gonderim = db.Column(db.Integer, default=0)
    durum = db.Column(db.String(20), default='beklemede')
    # beklemede, gonderildi, basarisiz
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    gonderen = db.relationship('User', backref=db.backref('toplu_mesajlar', lazy='dynamic'))
    alicilar = db.relationship('TopluMesajAlici', backref='toplu_mesaj', lazy='dynamic',
                               cascade='all, delete-orphan')

    @property
    def hedef_grup_str(self):
        hedef_map = {
            'tumu': 'Tümü',
            'ogretmenler': 'Öğretmenler',
            'veliler': 'Veliler',
            'personel': 'Personel',
            'sinif': 'Sınıf',
        }
        return hedef_map.get(self.hedef_grup, self.hedef_grup)

    @property
    def durum_badge(self):
        badge_map = {
            'beklemede': 'warning',
            'gonderildi': 'success',
            'basarisiz': 'danger',
        }
        return badge_map.get(self.durum, 'secondary')

    @property
    def durum_str(self):
        durum_map = {
            'beklemede': 'Beklemede',
            'gonderildi': 'Gönderildi',
            'basarisiz': 'Başarısız',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def gonderim_turu_str(self):
        turu_map = {
            'sistem': 'Sistem',
            'sms': 'SMS',
            'email': 'E-Posta',
        }
        return turu_map.get(self.gonderim_turu, self.gonderim_turu)

    def __repr__(self):
        return f'<TopluMesaj {self.baslik}>'


class TopluMesajAlici(db.Model):
    """Toplu Mesaj Alıcısı"""
    __tablename__ = 'toplu_mesaj_alicilari'

    id = db.Column(db.Integer, primary_key=True)
    toplu_mesaj_id = db.Column(db.Integer, db.ForeignKey('toplu_mesajlar.id'), nullable=False)
    alici_adi = db.Column(db.String(200), nullable=False)
    alici_iletisim = db.Column(db.String(200), nullable=False)
    durum = db.Column(db.String(20), default='beklemede')
    # gonderildi, basarisiz, beklemede
    hata_mesaji = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def durum_badge(self):
        badge_map = {
            'beklemede': 'warning',
            'gonderildi': 'success',
            'basarisiz': 'danger',
        }
        return badge_map.get(self.durum, 'secondary')

    @property
    def durum_str(self):
        durum_map = {
            'beklemede': 'Beklemede',
            'gonderildi': 'Gönderildi',
            'basarisiz': 'Başarısız',
        }
        return durum_map.get(self.durum, self.durum)

    def __repr__(self):
        return f'<TopluMesajAlici {self.alici_adi}>'


class MesajSablonu(db.Model):
    """Mesaj Şablonu"""
    __tablename__ = 'mesaj_sablonlari'

    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    icerik = db.Column(db.Text, nullable=False)
    kategori = db.Column(db.String(20), nullable=False, default='genel')
    # genel, devamsizlik, odeme, toplanti, sinav, diger
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    olusturan = db.relationship('User', backref=db.backref('mesaj_sablonlari', lazy='dynamic'))

    @property
    def kategori_str(self):
        kategori_map = {
            'genel': 'Genel',
            'devamsizlik': 'Devamsızlık',
            'odeme': 'Ödeme',
            'toplanti': 'Toplantı',
            'sinav': 'Sınav',
            'diger': 'Diğer',
        }
        return kategori_map.get(self.kategori, self.kategori)

    @property
    def kategori_badge(self):
        badge_map = {
            'genel': 'secondary',
            'devamsizlik': 'danger',
            'odeme': 'info',
            'toplanti': 'primary',
            'sinav': 'warning',
            'diger': 'dark',
        }
        return badge_map.get(self.kategori, 'secondary')

    def __repr__(self):
        return f'<MesajSablonu {self.baslik}>'


class IletisimDefteri(db.Model):
    """İletişim Defteri (Contact Book)"""
    __tablename__ = 'iletisim_defteri'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    soyad = db.Column(db.String(100), nullable=False)
    telefon = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=True)
    kurum = db.Column(db.String(200), nullable=True)
    gorev = db.Column(db.String(200), nullable=True)
    kategori = db.Column(db.String(20), nullable=False, default='diger')
    # veli, kurum, diger
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=True)
    yakinlik = db.Column(db.String(20), nullable=True)
    # anne, baba, vasi, diger
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    olusturan = db.relationship('User', backref=db.backref('iletisim_defteri', lazy='dynamic'))
    ogrenci = db.relationship('Ogrenci', backref=db.backref('iletisim_kayitlari', lazy='dynamic'))

    @property
    def tam_ad(self):
        return f"{self.ad} {self.soyad}"

    @property
    def kategori_str(self):
        kategori_map = {
            'veli': 'Veli',
            'kurum': 'Kurum',
            'diger': 'Diğer',
        }
        return kategori_map.get(self.kategori, self.kategori)

    @property
    def kategori_badge(self):
        badge_map = {
            'veli': 'primary',
            'kurum': 'success',
            'diger': 'secondary',
        }
        return badge_map.get(self.kategori, 'secondary')

    @property
    def yakinlik_str(self):
        yakinlik_map = {
            'anne': 'Anne',
            'baba': 'Baba',
            'vasi': 'Vasi',
            'diger': 'Diğer',
        }
        return yakinlik_map.get(self.yakinlik, self.yakinlik) if self.yakinlik else ''

    def __repr__(self):
        return f'<IletisimDefteri {self.ad} {self.soyad}>'
