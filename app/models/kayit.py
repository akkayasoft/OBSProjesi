from datetime import datetime, date
from app.extensions import db


class Sinif(db.Model):
    """Sınıf seviyesi (9, 10, 11, 12 vb.)"""
    __tablename__ = 'siniflar'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(50), nullable=False)  # "9. Sınıf", "10. Sınıf"
    seviye = db.Column(db.Integer, nullable=False)  # 9, 10, 11, 12
    aktif = db.Column(db.Boolean, default=True)

    subeler = db.relationship('Sube', backref='sinif', lazy='dynamic', order_by='Sube.ad')

    @property
    def ogrenci_sayisi(self):
        toplam = 0
        for sube in self.subeler.filter_by(aktif=True):
            toplam += sube.aktif_ogrenci_sayisi
        return toplam

    def __repr__(self):
        return f'<Sinif {self.ad}>'


class Sube(db.Model):
    """Şube (A, B, C vb.)"""
    __tablename__ = 'subeler'

    id = db.Column(db.Integer, primary_key=True)
    sinif_id = db.Column(db.Integer, db.ForeignKey('siniflar.id'), nullable=False)
    ad = db.Column(db.String(10), nullable=False)  # "A", "B", "C"
    kontenjan = db.Column(db.Integer, default=30)
    aktif = db.Column(db.Boolean, default=True)

    kayitlar = db.relationship('OgrenciKayit', backref='sube', lazy='dynamic')

    @property
    def tam_ad(self):
        return f"{self.sinif.ad} - {self.ad} Şubesi"

    @property
    def aktif_ogrenci_sayisi(self):
        return self.kayitlar.filter_by(durum='aktif').count()

    @property
    def bos_kontenjan(self):
        return self.kontenjan - self.aktif_ogrenci_sayisi

    def __repr__(self):
        return f'<Sube {self.sinif.ad}-{self.ad}>'


class KayitDonemi(db.Model):
    """Kayıt dönemi (2025-2026 vb.)"""
    __tablename__ = 'kayit_donemleri'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(20), unique=True, nullable=False)  # "2025-2026"
    baslangic_tarihi = db.Column(db.Date, nullable=False)
    bitis_tarihi = db.Column(db.Date, nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    aciklama = db.Column(db.Text, nullable=True)

    kayitlar = db.relationship('OgrenciKayit', backref='donem', lazy='dynamic')

    @property
    def ogrenci_sayisi(self):
        return self.kayitlar.filter_by(durum='aktif').count()

    @property
    def devam_ediyor_mu(self):
        return self.baslangic_tarihi <= date.today() <= self.bitis_tarihi

    def __repr__(self):
        return f'<KayitDonemi {self.ad}>'


class OgrenciKayit(db.Model):
    """Öğrenci kayıt bilgisi - öğrenciyi dönem ve sınıfa bağlar"""
    __tablename__ = 'ogrenci_kayitlari'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    donem_id = db.Column(db.Integer, db.ForeignKey('kayit_donemleri.id'), nullable=False)
    sube_id = db.Column(db.Integer, db.ForeignKey('subeler.id'), nullable=False)
    kayit_tarihi = db.Column(db.Date, nullable=False, default=date.today)
    durum = db.Column(db.String(20), nullable=False, default='aktif')
    # aktif, mezun, nakil_giden, nakil_gelen, dondurulan, kayit_silindi
    durum_tarihi = db.Column(db.Date, nullable=True)
    durum_aciklama = db.Column(db.Text, nullable=True)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('kayitlar', lazy='dynamic'))
    olusturan = db.relationship('User', backref='ogrenci_kayitlari')

    @property
    def sinif_sube(self):
        return f"{self.sube.sinif.ad} - {self.sube.ad}"

    @property
    def durum_badge(self):
        durum_map = {
            'aktif': ('Aktif', 'success'),
            'mezun': ('Mezun', 'primary'),
            'nakil_giden': ('Nakil Giden', 'warning'),
            'nakil_gelen': ('Nakil Gelen', 'info'),
            'dondurulan': ('Dondurulmuş', 'secondary'),
            'kayit_silindi': ('Kayıt Silindi', 'danger'),
        }
        return durum_map.get(self.durum, ('Bilinmiyor', 'secondary'))

    def __repr__(self):
        return f'<OgrenciKayit {self.ogrenci_id} {self.donem_id}>'


class VeliBilgisi(db.Model):
    """Detaylı veli bilgileri"""
    __tablename__ = 'veli_bilgileri'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, unique=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    yakinlik = db.Column(db.String(20), nullable=False)  # anne, baba, vasi
    tc_kimlik = db.Column(db.String(11), nullable=True)
    ad = db.Column(db.String(100), nullable=False)
    soyad = db.Column(db.String(100), nullable=False)
    telefon = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    meslek = db.Column(db.String(100), nullable=True)
    adres = db.Column(db.Text, nullable=True)

    user = db.relationship('User', backref=db.backref('veli_bilgisi', uselist=False))
    ogrenci = db.relationship('Ogrenci', backref=db.backref('veli_bilgileri', lazy='dynamic'))

    @property
    def tam_ad(self):
        return f"{self.ad} {self.soyad}"

    def __repr__(self):
        return f'<VeliBilgisi {self.yakinlik}: {self.ad} {self.soyad}>'


class OgrenciBelge(db.Model):
    """Öğrenci belge takibi"""
    __tablename__ = 'ogrenci_belgeleri'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    belge_turu = db.Column(db.String(50), nullable=False)
    # karteks, nufus_cuzdani, ogrenim_belgesi, fotograf, saglik_raporu, ikametgah, nakil_belgesi, diger
    teslim_edildi = db.Column(db.Boolean, default=False)
    teslim_tarihi = db.Column(db.Date, nullable=True)
    dosya_yolu = db.Column(db.String(300), nullable=True)
    orijinal_ad = db.Column(db.String(255), nullable=True)
    aciklama = db.Column(db.Text, nullable=True)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('belgeler', lazy='dynamic'))

    @property
    def belge_turu_ad(self):
        tur_map = {
            'karteks': 'Kayıt Karteksi',
            'nufus_cuzdani': 'Nüfus Cüzdanı Fotokopisi',
            'ogrenim_belgesi': 'Öğrenim Belgesi',
            'fotograf': 'Vesikalık Fotoğraf',
            'saglik_raporu': 'Sağlık Raporu',
            'ikametgah': 'İkametgah Belgesi',
            'nakil_belgesi': 'Nakil Belgesi',
            'diger': 'Diğer',
        }
        return tur_map.get(self.belge_turu, self.belge_turu)

    def __repr__(self):
        return f'<OgrenciBelge {self.belge_turu} {self.teslim_edildi}>'
