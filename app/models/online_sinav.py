from datetime import datetime
from app.extensions import db


class OnlineSinav(db.Model):
    """Online Sinav"""
    __tablename__ = 'online_sinavlar'

    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    ders_id = db.Column(db.Integer, db.ForeignKey('dersler.id'), nullable=False)
    sube_id = db.Column(db.Integer, db.ForeignKey('subeler.id'), nullable=True)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sure = db.Column(db.Integer, nullable=False)  # dakika
    baslangic_zamani = db.Column(db.DateTime, nullable=False)
    bitis_zamani = db.Column(db.DateTime, nullable=False)
    sinav_turu = db.Column(db.String(20), nullable=False, default='test')
    # test, klasik, karisik
    zorluk = db.Column(db.String(20), nullable=False, default='orta')
    # kolay, orta, zor
    toplam_puan = db.Column(db.Float, default=100)
    gecme_puani = db.Column(db.Float, default=50)
    sorulari_karistir = db.Column(db.Boolean, default=False)
    secenekleri_karistir = db.Column(db.Boolean, default=False)
    sonuclari_goster = db.Column(db.Boolean, default=True)
    aktif = db.Column(db.Boolean, default=True)
    donem = db.Column(db.String(20), default='2025-2026')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    ders = db.relationship('Ders', backref=db.backref('online_sinavlar', lazy='dynamic'))
    sube = db.relationship('Sube', backref=db.backref('online_sinavlar', lazy='dynamic'))
    olusturan = db.relationship('User', backref=db.backref('online_sinavlar', lazy='dynamic'))
    sorular = db.relationship('SinavSoru', backref='sinav', lazy='dynamic',
                              cascade='all, delete-orphan',
                              order_by='SinavSoru.sira')
    katilimlar = db.relationship('SinavKatilim', backref='sinav', lazy='dynamic',
                                 cascade='all, delete-orphan')

    @property
    def sinav_turu_str(self):
        turu_map = {
            'test': 'Test',
            'klasik': 'Klasik',
            'karisik': 'Karışık',
        }
        return turu_map.get(self.sinav_turu, self.sinav_turu)

    @property
    def zorluk_str(self):
        zorluk_map = {
            'kolay': 'Kolay',
            'orta': 'Orta',
            'zor': 'Zor',
        }
        return zorluk_map.get(self.zorluk, self.zorluk)

    @property
    def zorluk_badge(self):
        badge_map = {
            'kolay': 'success',
            'orta': 'warning',
            'zor': 'danger',
        }
        return badge_map.get(self.zorluk, 'secondary')

    @property
    def durum(self):
        now = datetime.utcnow()
        if not self.aktif:
            return 'pasif'
        if now < self.baslangic_zamani:
            return 'yaklasan'
        if now > self.bitis_zamani:
            return 'bitmis'
        return 'aktif'

    @property
    def durum_str(self):
        durum_map = {
            'aktif': 'Aktif',
            'yaklasan': 'Yaklaşan',
            'bitmis': 'Bitmiş',
            'pasif': 'Pasif',
        }
        return durum_map.get(self.durum, 'Bilinmiyor')

    @property
    def durum_badge(self):
        badge_map = {
            'aktif': 'success',
            'yaklasan': 'warning',
            'bitmis': 'secondary',
            'pasif': 'dark',
        }
        return badge_map.get(self.durum, 'secondary')

    @property
    def soru_sayisi(self):
        return self.sorular.count()

    @property
    def katilimci_sayisi(self):
        return self.katilimlar.count()

    @property
    def tamamlanan_sayisi(self):
        return self.katilimlar.filter_by(durum='tamamlandi').count()

    @property
    def ortalama_puan(self):
        tamamlananlar = self.katilimlar.filter(
            SinavKatilim.durum.in_(['tamamlandi', 'suresi_doldu']),
            SinavKatilim.toplam_puan.isnot(None)
        ).all()
        if not tamamlananlar:
            return 0
        return round(sum(k.toplam_puan for k in tamamlananlar) / len(tamamlananlar), 1)

    def __repr__(self):
        return f'<OnlineSinav {self.baslik}>'


class SinavSoru(db.Model):
    """Sinav Sorusu"""
    __tablename__ = 'sinav_sorulari'

    id = db.Column(db.Integer, primary_key=True)
    sinav_id = db.Column(db.Integer, db.ForeignKey('online_sinavlar.id'), nullable=False)
    soru_metni = db.Column(db.Text, nullable=False)
    soru_turu = db.Column(db.String(20), nullable=False)
    # coktan_secmeli, dogru_yanlis, klasik, bosluk_doldurma
    puan = db.Column(db.Float, nullable=False)
    sira = db.Column(db.Integer, nullable=False, default=1)
    zorluk = db.Column(db.String(20), nullable=False, default='orta')
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    secenekler = db.relationship('SoruSecenegi', backref='soru', lazy='dynamic',
                                 cascade='all, delete-orphan',
                                 order_by='SoruSecenegi.sira')
    cevaplar = db.relationship('OgrenciCevap', backref='soru', lazy='dynamic',
                               cascade='all, delete-orphan')

    @property
    def soru_turu_str(self):
        turu_map = {
            'coktan_secmeli': 'Çoktan Seçmeli',
            'dogru_yanlis': 'Doğru/Yanlış',
            'klasik': 'Klasik',
            'bosluk_doldurma': 'Boşluk Doldurma',
        }
        return turu_map.get(self.soru_turu, self.soru_turu)

    @property
    def soru_turu_badge(self):
        badge_map = {
            'coktan_secmeli': 'primary',
            'dogru_yanlis': 'info',
            'klasik': 'warning',
            'bosluk_doldurma': 'success',
        }
        return badge_map.get(self.soru_turu, 'secondary')

    @property
    def dogru_secenek(self):
        return self.secenekler.filter_by(dogru_mu=True).first()

    def __repr__(self):
        return f'<SinavSoru {self.id} sinav={self.sinav_id}>'


class SoruSecenegi(db.Model):
    """Soru Secenegi (coktan secmeli icin)"""
    __tablename__ = 'soru_secenekleri'

    id = db.Column(db.Integer, primary_key=True)
    soru_id = db.Column(db.Integer, db.ForeignKey('sinav_sorulari.id'), nullable=False)
    secenek_metni = db.Column(db.Text, nullable=False)
    sira = db.Column(db.Integer, nullable=False, default=1)
    dogru_mu = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SoruSecenegi {self.id} soru={self.soru_id}>'


class SinavKatilim(db.Model):
    """Sinav Katilim"""
    __tablename__ = 'sinav_katilimlari'

    id = db.Column(db.Integer, primary_key=True)
    sinav_id = db.Column(db.Integer, db.ForeignKey('online_sinavlar.id'), nullable=False)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    baslama_zamani = db.Column(db.DateTime, nullable=True)
    bitirme_zamani = db.Column(db.DateTime, nullable=True)
    toplam_puan = db.Column(db.Float, nullable=True)
    durum = db.Column(db.String(20), nullable=False, default='baslamadi')
    # baslamadi, devam_ediyor, tamamlandi, suresi_doldu
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('sinav_id', 'ogrenci_id', name='uq_online_sinav_katilim'),
    )

    ogrenci = db.relationship('Ogrenci', backref=db.backref('sinav_katilimlari', lazy='dynamic'))
    cevaplar = db.relationship('OgrenciCevap', backref='katilim', lazy='dynamic',
                               cascade='all, delete-orphan')

    @property
    def durum_str(self):
        durum_map = {
            'baslamadi': 'Başlamadı',
            'devam_ediyor': 'Devam Ediyor',
            'tamamlandi': 'Tamamlandı',
            'suresi_doldu': 'Süresi Doldu',
        }
        return durum_map.get(self.durum, self.durum)

    @property
    def durum_badge(self):
        badge_map = {
            'baslamadi': 'secondary',
            'devam_ediyor': 'warning',
            'tamamlandi': 'success',
            'suresi_doldu': 'danger',
        }
        return badge_map.get(self.durum, 'secondary')

    @property
    def gecti_mi(self):
        if self.toplam_puan is None:
            return None
        return self.toplam_puan >= self.sinav.gecme_puani

    def __repr__(self):
        return f'<SinavKatilim sinav={self.sinav_id} ogrenci={self.ogrenci_id}>'


class OgrenciCevap(db.Model):
    """Ogrenci Cevap"""
    __tablename__ = 'ogrenci_cevaplari'

    id = db.Column(db.Integer, primary_key=True)
    katilim_id = db.Column(db.Integer, db.ForeignKey('sinav_katilimlari.id'), nullable=False)
    soru_id = db.Column(db.Integer, db.ForeignKey('sinav_sorulari.id'), nullable=False)
    cevap_metni = db.Column(db.Text, nullable=True)
    secilen_secenek_id = db.Column(db.Integer, db.ForeignKey('soru_secenekleri.id'), nullable=True)
    dogru_yanlis_cevap = db.Column(db.Boolean, nullable=True)
    puan = db.Column(db.Float, nullable=True)
    dogru_mu = db.Column(db.Boolean, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    secilen_secenek = db.relationship('SoruSecenegi', backref=db.backref('cevaplar', lazy='dynamic'))

    def __repr__(self):
        return f'<OgrenciCevap katilim={self.katilim_id} soru={self.soru_id}>'
