"""Deneme Sinavi modelleri — YKS (TYT/AYT/YDT), LGS, MSU vb. sinavlar.

Ortak okul-ici sinavdan (`ortak_sinav.py`) farki: cok dersli tek oturum,
her ders icin ayri dogru/yanlis/bos/net, tip (tyt/ayt/lgs...) ve yaklasik
puan turu hesaplamalari.
"""
from datetime import datetime, date
from app.extensions import db


SINAV_TIPLERI = [
    ('tyt', 'YKS - TYT (Temel Yeterlilik)'),
    ('ayt_say', 'YKS - AYT Sayisal'),
    ('ayt_soz', 'YKS - AYT Sozel'),
    ('ayt_ea', 'YKS - AYT Esit Agirlik'),
    ('ayt_dil', 'YKS - AYT Dil (YDT)'),
    ('lgs', 'LGS (Liselere Gecis)'),
    ('msu', 'MSU (Askeri)'),
    ('ozel', 'Ozel / Serbest'),
]

DURUM_TIPLERI = [
    ('hazirlaniyor', 'Hazirlaniyor'),
    ('yayinlandi', 'Yayinlandi'),
    ('uygulandi', 'Uygulandi'),
    ('tamamlandi', 'Tamamlandi'),
]


class DenemeSinavi(db.Model):
    """Bir deneme sinavi oturumu (ornek: 'TYT Genel Deneme #4 Mart 2026')."""
    __tablename__ = 'deneme_sinavlari'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(200), nullable=False)
    sinav_tipi = db.Column(db.String(20), nullable=False, index=True)
    donem = db.Column(db.String(20), nullable=False)  # 2025-2026
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    # Hedef seviye: LGS icin '8', TYT/AYT icin '11','12','mezun' vs.
    hedef_seviye = db.Column(db.String(20), nullable=True)
    sure_dakika = db.Column(db.Integer, nullable=False, default=135)
    durum = db.Column(db.String(20), nullable=False, default='hazirlaniyor', index=True)
    aciklama = db.Column(db.Text, nullable=True)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    olusturan = db.relationship('User', backref=db.backref('olusturdugu_denemeler', lazy='dynamic'))
    dersler = db.relationship('DenemeDersi', backref='sinav', lazy='dynamic',
                              cascade='all, delete-orphan',
                              order_by='DenemeDersi.sira')
    katilimlar = db.relationship('DenemeKatilim', backref='sinav', lazy='dynamic',
                                 cascade='all, delete-orphan')

    @property
    def tip_str(self):
        return dict(SINAV_TIPLERI).get(self.sinav_tipi, self.sinav_tipi)

    @property
    def durum_str(self):
        return dict(DURUM_TIPLERI).get(self.durum, self.durum)

    @property
    def durum_badge(self):
        return {
            'hazirlaniyor': 'secondary',
            'yayinlandi': 'info',
            'uygulandi': 'primary',
            'tamamlandi': 'success',
        }.get(self.durum, 'secondary')

    @property
    def toplam_soru(self):
        return sum((d.soru_sayisi or 0) for d in self.dersler)

    @property
    def katilimci_sayisi(self):
        return self.katilimlar.filter_by(katildi=True).count()

    @property
    def ortalama_net(self):
        """Tum katilimcilarin ortalama toplam neti."""
        from sqlalchemy import func
        q = db.session.query(func.avg(DenemeKatilim.toplam_net)).filter(
            DenemeKatilim.deneme_sinavi_id == self.id,
            DenemeKatilim.katildi.is_(True),
        )
        val = q.scalar()
        return round(val, 2) if val else 0.0

    @property
    def ortalama_puan(self):
        from sqlalchemy import func
        q = db.session.query(func.avg(DenemeKatilim.toplam_puan)).filter(
            DenemeKatilim.deneme_sinavi_id == self.id,
            DenemeKatilim.katildi.is_(True),
        )
        val = q.scalar()
        return round(val, 2) if val else 0.0

    def __repr__(self):
        return f'<DenemeSinavi {self.ad}>'


class DenemeDersi(db.Model):
    """Bir deneme sinavindaki ders/test blogu (ornek: TYT'nin 'Turkce 40 soru' blogu)."""
    __tablename__ = 'deneme_dersleri'

    id = db.Column(db.Integer, primary_key=True)
    deneme_sinavi_id = db.Column(db.Integer, db.ForeignKey('deneme_sinavlari.id'),
                                 nullable=False, index=True)
    ders_kodu = db.Column(db.String(40), nullable=False)  # 'turkce','matematik'...
    ders_adi = db.Column(db.String(100), nullable=False)  # 'Turkce', 'Temel Matematik'
    soru_sayisi = db.Column(db.Integer, nullable=False, default=20)
    sira = db.Column(db.Integer, nullable=False, default=0)
    # Puan hesabinda kullanilacak katsayi (ortalama: sinav_tipi'ne ve derse bagli)
    katsayi = db.Column(db.Float, nullable=True)
    # Alt-alan etiketi (ornek: AYT-SAY icin 'say', AYT-SOZ icin 'soz')
    alan = db.Column(db.String(20), nullable=True)

    sonuclar = db.relationship('DenemeDersSonucu', backref='ders', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return f'<DenemeDersi {self.ders_adi} ({self.soru_sayisi})>'


class DenemeKatilim(db.Model):
    """Bir ogrencinin bir deneme sinavina katilimi (cache + meta)."""
    __tablename__ = 'deneme_katilimlari'
    __table_args__ = (
        db.UniqueConstraint('deneme_sinavi_id', 'ogrenci_id',
                            name='uq_deneme_katilim_ogrenci'),
    )

    id = db.Column(db.Integer, primary_key=True)
    deneme_sinavi_id = db.Column(db.Integer, db.ForeignKey('deneme_sinavlari.id'),
                                 nullable=False, index=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'),
                           nullable=False, index=True)
    sube_id = db.Column(db.Integer, db.ForeignKey('subeler.id'), nullable=True)
    katildi = db.Column(db.Boolean, nullable=False, default=True)
    obp = db.Column(db.Float, nullable=True)  # Okul Basari Puani (opsiyonel)
    toplam_dogru = db.Column(db.Integer, nullable=True)
    toplam_yanlis = db.Column(db.Integer, nullable=True)
    toplam_bos = db.Column(db.Integer, nullable=True)
    toplam_net = db.Column(db.Float, nullable=True)
    # Sinav tipine gore yaklasik puan (TYT: tek puan; AYT: ilgili alan puani)
    toplam_puan = db.Column(db.Float, nullable=True)
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    ogrenci = db.relationship('Ogrenci',
                              backref=db.backref('deneme_katilimlari', lazy='dynamic'))
    sube = db.relationship('Sube',
                           backref=db.backref('deneme_katilimlari', lazy='dynamic'))
    ders_sonuclari = db.relationship('DenemeDersSonucu', backref='katilim',
                                     lazy='dynamic', cascade='all, delete-orphan')

    def hesapla_toplamlari(self):
        """ders_sonuclari'ndan toplam D/Y/B/net degerlerini hesapla."""
        sonuclar = self.ders_sonuclari.all()
        self.toplam_dogru = sum((s.dogru or 0) for s in sonuclar)
        self.toplam_yanlis = sum((s.yanlis or 0) for s in sonuclar)
        self.toplam_bos = sum((s.bos or 0) for s in sonuclar)
        self.toplam_net = round(sum((s.net or 0) for s in sonuclar), 2)

    def __repr__(self):
        return f'<DenemeKatilim sinav={self.deneme_sinavi_id} ogrenci={self.ogrenci_id}>'


class DenemeDersSonucu(db.Model):
    """Ders bazli D/Y/B/net sonucu."""
    __tablename__ = 'deneme_ders_sonuclari'
    __table_args__ = (
        db.UniqueConstraint('katilim_id', 'deneme_dersi_id',
                            name='uq_deneme_ders_sonucu'),
    )

    id = db.Column(db.Integer, primary_key=True)
    katilim_id = db.Column(db.Integer, db.ForeignKey('deneme_katilimlari.id'),
                           nullable=False, index=True)
    deneme_dersi_id = db.Column(db.Integer, db.ForeignKey('deneme_dersleri.id'),
                                nullable=False, index=True)
    dogru = db.Column(db.Integer, nullable=False, default=0)
    yanlis = db.Column(db.Integer, nullable=False, default=0)
    bos = db.Column(db.Integer, nullable=False, default=0)
    net = db.Column(db.Float, nullable=True)

    def hesapla_net(self):
        """net = dogru - yanlis/4 (Turkiye standarti)."""
        d = self.dogru or 0
        y = self.yanlis or 0
        self.net = round(d - (y / 4.0), 2)

    def __repr__(self):
        return (f'<DenemeDersSonucu d={self.dogru} y={self.yanlis} '
                f'b={self.bos} net={self.net}>')


# OMR (Optik Form Okuma) modelleri -------------------------------------------

class CevapAnahtari(db.Model):
    """Bir deneme dersinin resmi cevap anahtari (her soru icin dogru sik).

    OMR pipeline'inda ogrencinin okunan cevaplarini bu anahtarla karsilastirip
    D/Y/B uretiriz. Bir ders icin dersin soru_sayisi kadar satir bulunur.
    """
    __tablename__ = 'deneme_cevap_anahtari'
    __table_args__ = (
        db.UniqueConstraint('deneme_dersi_id', 'soru_no',
                            name='uq_cevap_anahtari_ders_soru'),
    )

    id = db.Column(db.Integer, primary_key=True)
    deneme_dersi_id = db.Column(db.Integer, db.ForeignKey('deneme_dersleri.id'),
                                nullable=False, index=True)
    soru_no = db.Column(db.Integer, nullable=False)  # 1..N
    # A/B/C/D/E (LGS'de 4 sik olur, TYT/AYT'de 5 sik)
    dogru_cevap = db.Column(db.String(1), nullable=False)
    # Iptal edilen sorular icin (dogru sayilir)
    iptal = db.Column(db.Boolean, nullable=False, default=False)

    ders = db.relationship('DenemeDersi',
                           backref=db.backref('cevap_anahtari', lazy='dynamic',
                                              cascade='all, delete-orphan',
                                              order_by='CevapAnahtari.soru_no'))

    def __repr__(self):
        return f'<CevapAnahtari ders={self.deneme_dersi_id} s{self.soru_no}={self.dogru_cevap}>'


class OmrTarama(db.Model):
    """Bir deneme sinavi icin yuklenen OMR tarama/fotografi (audit + debug).

    Admin 'Fotograflari yukle' akisindan her ogrencinin cevap kagidini OMR'la
    okutur; bu tablo yuklenen dosya, sonuc ozeti ve hata mesajlarini tutar.
    Uretilen `DenemeKatilim` ile eslesir.
    """
    __tablename__ = 'deneme_omr_taramalari'

    id = db.Column(db.Integer, primary_key=True)
    deneme_sinavi_id = db.Column(db.Integer, db.ForeignKey('deneme_sinavlari.id'),
                                 nullable=False, index=True)
    katilim_id = db.Column(db.Integer, db.ForeignKey('deneme_katilimlari.id'),
                           nullable=True, index=True)
    ogrenci_no = db.Column(db.String(40), nullable=True, index=True)  # OMR'dan okunan
    dosya_adi = db.Column(db.String(255), nullable=True)
    durum = db.Column(db.String(20), nullable=False, default='bekliyor')
    # bekliyor / basarili / hata / eslenemedi
    hata_mesaji = db.Column(db.Text, nullable=True)
    # Ham okunmus cevaplar JSON: [{"soru": 1, "cevap": "B"}, ...]
    ham_cevaplar_json = db.Column(db.Text, nullable=True)
    toplam_dogru = db.Column(db.Integer, nullable=True)
    toplam_yanlis = db.Column(db.Integer, nullable=True)
    toplam_bos = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sinav = db.relationship('DenemeSinavi',
                            backref=db.backref('omr_taramalari', lazy='dynamic',
                                               cascade='all, delete-orphan'))
    katilim = db.relationship('DenemeKatilim',
                              backref=db.backref('omr_taramalari', lazy='dynamic'))

    def __repr__(self):
        return f'<OmrTarama sinav={self.deneme_sinavi_id} dosya={self.dosya_adi} {self.durum}>'
