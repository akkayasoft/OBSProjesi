from datetime import datetime, date
from app.extensions import db


class Gorusme(db.Model):
    """Rehberlik Gorusmesi (Counseling Session)"""
    __tablename__ = 'rehberlik_gorusmeleri'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    rehber_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    gorusme_tarihi = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    gorusme_turu = db.Column(db.String(20), nullable=False, default='bireysel')
    # bireysel, grup, veli, kriz
    konu = db.Column(db.String(200), nullable=False)
    icerik = db.Column(db.Text, nullable=True)
    sonuc_ve_oneri = db.Column(db.Text, nullable=True)
    gizlilik_seviyesi = db.Column(db.String(20), nullable=False, default='normal')
    # normal, gizli, cok_gizli
    durum = db.Column(db.String(20), nullable=False, default='planlandi')
    # planlandi, tamamlandi, iptal
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('rehberlik_gorusmeleri', lazy='dynamic'))
    rehber = db.relationship('User', backref=db.backref('rehberlik_gorusmeleri', lazy='dynamic'))

    @property
    def gorusme_turu_str(self):
        tur_map = {
            'bireysel': 'Bireysel',
            'grup': 'Grup',
            'veli': 'Veli',
            'kriz': 'Kriz',
        }
        return tur_map.get(self.gorusme_turu, self.gorusme_turu)

    @property
    def gorusme_turu_badge(self):
        badge_map = {
            'bireysel': 'primary',
            'grup': 'info',
            'veli': 'success',
            'kriz': 'danger',
        }
        return badge_map.get(self.gorusme_turu, 'secondary')

    @property
    def gizlilik_str(self):
        gizlilik_map = {
            'normal': 'Normal',
            'gizli': 'Gizli',
            'cok_gizli': 'Cok Gizli',
        }
        return gizlilik_map.get(self.gizlilik_seviyesi, self.gizlilik_seviyesi)

    @property
    def gizlilik_badge(self):
        badge_map = {
            'normal': 'secondary',
            'gizli': 'warning',
            'cok_gizli': 'danger',
        }
        return badge_map.get(self.gizlilik_seviyesi, 'secondary')

    @property
    def durum_str(self):
        durum_map = {
            'planlandi': 'Planlandi',
            'tamamlandi': 'Tamamlandi',
            'iptal': 'Iptal',
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
        return f'<Gorusme {self.konu}>'


class OgrenciProfil(db.Model):
    """Ogrenci Rehberlik Profili"""
    __tablename__ = 'rehberlik_profilleri'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False, unique=True)
    aile_durumu = db.Column(db.String(20), nullable=False, default='normal')
    # normal, bosanmis, tek_ebeveyn, vefat, diger
    kardes_sayisi = db.Column(db.Integer, nullable=True, default=0)
    ekonomik_durum = db.Column(db.String(20), nullable=True, default='orta')
    # iyi, orta, dusuk
    saglik_durumu = db.Column(db.Text, nullable=True)
    ozel_not = db.Column(db.Text, nullable=True)
    ilgi_alanlari = db.Column(db.Text, nullable=True)
    guclu_yonler = db.Column(db.Text, nullable=True)
    gelistirilecek_yonler = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('rehberlik_profili', uselist=False))

    @property
    def aile_durumu_str(self):
        durum_map = {
            'normal': 'Normal',
            'bosanmis': 'Bosanmis',
            'tek_ebeveyn': 'Tek Ebeveyn',
            'vefat': 'Vefat',
            'diger': 'Diger',
        }
        return durum_map.get(self.aile_durumu, self.aile_durumu)

    @property
    def ekonomik_durum_str(self):
        durum_map = {
            'iyi': 'Iyi',
            'orta': 'Orta',
            'dusuk': 'Dusuk',
        }
        return durum_map.get(self.ekonomik_durum, self.ekonomik_durum)

    @property
    def ekonomik_durum_badge(self):
        badge_map = {
            'iyi': 'success',
            'orta': 'warning',
            'dusuk': 'danger',
        }
        return badge_map.get(self.ekonomik_durum, 'secondary')

    def __repr__(self):
        return f'<OgrenciProfil ogrenci_id={self.ogrenci_id}>'


class DavranisKaydi(db.Model):
    """Davranis Kaydi (Behavior Record)"""
    __tablename__ = 'davranis_kayitlari'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    kaydeden_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    tur = db.Column(db.String(20), nullable=False, default='olumlu')
    # olumlu, olumsuz
    kategori = db.Column(db.String(20), nullable=False, default='diger')
    # basari, katilim, saygi, sorumluluk, siddet, devamsizlik, diger
    aciklama = db.Column(db.Text, nullable=False)
    alinan_onlem = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('davranis_kayitlari', lazy='dynamic'))
    kaydeden = db.relationship('User', backref=db.backref('davranis_kayitlari', lazy='dynamic'))

    @property
    def tur_str(self):
        tur_map = {
            'olumlu': 'Olumlu',
            'olumsuz': 'Olumsuz',
        }
        return tur_map.get(self.tur, self.tur)

    @property
    def tur_badge(self):
        badge_map = {
            'olumlu': 'success',
            'olumsuz': 'danger',
        }
        return badge_map.get(self.tur, 'secondary')

    @property
    def kategori_str(self):
        kategori_map = {
            'basari': 'Basari',
            'katilim': 'Katilim',
            'saygi': 'Saygi',
            'sorumluluk': 'Sorumluluk',
            'siddet': 'Siddet',
            'devamsizlik': 'Devamsizlik',
            'diger': 'Diger',
        }
        return kategori_map.get(self.kategori, self.kategori)

    @property
    def kategori_badge(self):
        badge_map = {
            'basari': 'primary',
            'katilim': 'info',
            'saygi': 'success',
            'sorumluluk': 'warning',
            'siddet': 'danger',
            'devamsizlik': 'dark',
            'diger': 'secondary',
        }
        return badge_map.get(self.kategori, 'secondary')

    def __repr__(self):
        return f'<DavranisKaydi {self.tur} {self.kategori}>'


class VeliGorusmesi(db.Model):
    """Veli Gorusmesi (Parent Meeting)"""
    __tablename__ = 'veli_gorusmeleri'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    veli_adi = db.Column(db.String(200), nullable=False)
    veli_telefon = db.Column(db.String(20), nullable=True)
    gorusme_tarihi = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    gorusme_turu = db.Column(db.String(20), nullable=False, default='yuz_yuze')
    # yuz_yuze, telefon, online
    konu = db.Column(db.String(200), nullable=False)
    icerik = db.Column(db.Text, nullable=True)
    sonuc = db.Column(db.Text, nullable=True)
    gorusen_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('veli_gorusmeleri', lazy='dynamic'))
    gorusen = db.relationship('User', backref=db.backref('veli_gorusmeleri', lazy='dynamic'))

    @property
    def gorusme_turu_str(self):
        tur_map = {
            'yuz_yuze': 'Yuz Yuze',
            'telefon': 'Telefon',
            'online': 'Online',
        }
        return tur_map.get(self.gorusme_turu, self.gorusme_turu)

    @property
    def gorusme_turu_badge(self):
        badge_map = {
            'yuz_yuze': 'primary',
            'telefon': 'info',
            'online': 'success',
        }
        return badge_map.get(self.gorusme_turu, 'secondary')

    def __repr__(self):
        return f'<VeliGorusmesi {self.konu}>'


class RehberlikPlani(db.Model):
    """Rehberlik Plani (Guidance Plan)"""
    __tablename__ = 'rehberlik_planlari'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    rehber_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    baslik = db.Column(db.String(200), nullable=False)
    hedefler = db.Column(db.Text, nullable=True)
    uygulanacak_yontemler = db.Column(db.Text, nullable=True)
    baslangic_tarihi = db.Column(db.Date, nullable=False, default=date.today)
    bitis_tarihi = db.Column(db.Date, nullable=True)
    durum = db.Column(db.String(20), nullable=False, default='aktif')
    # aktif, tamamlandi, beklemede
    degerlendirme = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci', backref=db.backref('rehberlik_planlari', lazy='dynamic'))
    rehber = db.relationship('User', backref=db.backref('rehberlik_planlari', lazy='dynamic'))

    @property
    def durum_str(self):
        durum_map = {
            'aktif': 'Aktif',
            'tamamlandi': 'Tamamlandi',
            'beklemede': 'Beklemede',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        badge_map = {
            'aktif': 'success',
            'tamamlandi': 'primary',
            'beklemede': 'warning',
        }
        return badge_map.get(self.durum, 'secondary')

    def __repr__(self):
        return f'<RehberlikPlani {self.baslik}>'


class RiskSkoruGecmisi(db.Model):
    """Ogrenci risk skoru haftalik snapshot.

    Erken uyari sisteminin uygulanan plan/gorusme sonrasi etkinligini
    olcebilmek icin haftalik (veya manuel) snapshot saklanir.
    """
    __tablename__ = 'risk_skoru_gecmisi'
    __table_args__ = (
        db.UniqueConstraint('ogrenci_id', 'snapshot_tarih',
                            name='uq_risk_gecmisi_ogrenci_tarih'),
        db.Index('ix_risk_gecmisi_tarih', 'snapshot_tarih'),
    )

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    snapshot_tarih = db.Column(db.Date, nullable=False, default=date.today)
    skor = db.Column(db.Integer, nullable=False)
    seviye = db.Column(db.String(10), nullable=False)
    # dusuk, orta, yuksek
    devamsizlik_gun = db.Column(db.Integer, nullable=False, default=0)
    olumsuz_davranis = db.Column(db.Integer, nullable=False, default=0)
    deneme_trend = db.Column(db.String(20), nullable=True)
    # yukseliyor, dusuyor, sabit, yetersiz, None
    sebepler = db.Column(db.Text, nullable=True)  # CSV
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci',
                              backref=db.backref('risk_skoru_gecmisi', lazy='dynamic'))

    @property
    def seviye_badge(self):
        return {'dusuk': 'success', 'orta': 'warning', 'yuksek': 'danger'}.get(
            self.seviye, 'secondary')

    def __repr__(self):
        return f'<RiskSkoruGecmisi {self.ogrenci_id} {self.snapshot_tarih} {self.skor}>'
