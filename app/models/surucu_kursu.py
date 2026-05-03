"""Surucu kursu modulu modelleri.

Sadece kurum_tipi='surucu_kursu' olan tenant'lar tarafindan kullanilir.
Mevcut OBS modellerinden (Ogrenci, OgrenciTaksit) bagimsiz — dershane
tenant'larini etkilemez.

Tablolar her tenant DB'sinde olusturulur (db.metadata.create_all
calistiginda) ama dershane tenant'larinda bos kalir, hicbir kod o
tablolara dokunmaz.
"""
from datetime import datetime
from app.extensions import db


# Turkiye'de gecerli tum ehliyet siniflari (Karayollari Trafik
# Yonetmeligi'ne gore). UI'da dropdown olarak gosterilir.
EHLIYET_SINIFLARI = [
    # Motosiklet
    ('M',          'M (Motorlu Bisiklet)'),
    ('A1',         'A1 (125cc Altı Motosiklet)'),
    ('A2',         'A2 (35 kW Altı Motosiklet)'),
    ('A',          'A (Sınırsız Motosiklet)'),
    ('A1_gecis',   'A1 Sınıfı Geçiş'),
    ('A2_gecis',   'A2 Sınıfı Geçiş'),
    ('A_gecis',    'A Sınıfı Geçiş'),
    # Otomobil + ATV
    ('B1',         'B1 (4 Tekerlekli Motosiklet/ATV)'),
    ('B_manuel',   'B Sınıfı Manuel'),
    ('B_otomatik', 'B Sınıfı Otomatik'),
    ('B_gecis',    'B Sınıfı Geçiş'),
    ('BE',         'BE (B + Römork)'),
    # Kamyon / agir vasita
    ('C1',         'C1 (Küçük Kamyon)'),
    ('C',          'C (Kamyon)'),
    ('C1E',        'C1E (C1 + Römork)'),
    ('CE',         'CE (Kamyon + Römork)'),
    # Otobus / minibus
    ('D1',         'D1 (Minibüs)'),
    ('D',          'D (Otobüs)'),
    ('D1E',        'D1E (D1 + Römork)'),
    ('DE',         'DE (Otobüs + Römork)'),
    # Diger
    ('F',          'F (Traktör)'),
    ('G',          'G (İş Makinesi)'),
    ('ozel_ders',  'Özel Ders (Kayıtsız Aday)'),
    # Mesleki yeterlilik (SRC) ve psikoteknik
    ('SRC1',       'SRC1 (Yurt İçi Yolcu Taşımacılığı)'),
    ('SRC2',       'SRC2 (Yurt Dışı Yolcu Taşımacılığı)'),
    ('SRC3',       'SRC3 (Yurt İçi Eşya/Kargo)'),
    ('SRC4',       'SRC4 (Yurt Dışı Eşya/Kargo)'),
    ('SRC5',       'SRC5 (Tehlikeli Madde – ADR)'),
    ('psikoteknik','Psikoteknik Değerlendirme'),
]

EHLIYET_SINIF_DICT = dict(EHLIYET_SINIFLARI)


class Kursiyer(db.Model):
    """Surucu kursunda egitim alan aday.

    OBS Ogrenci modelinden ayri tutuldu cunku alanlar farkli (telefon
    vs tc_kimlik, ehliyet_sinifi vs sinif_no, ders_sayisi vs kayit_donemi).
    """
    __tablename__ = 'kursiyerler'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    soyad = db.Column(db.String(100), nullable=False)
    telefon = db.Column(db.String(40), nullable=True, index=True)

    # Kayit donemi: ay/yil bazli (form'da date input ama gun ignore edilir)
    kayit_tarihi = db.Column(db.Date, nullable=False, default=datetime.utcnow)

    ehliyet_sinifi = db.Column(db.String(20), nullable=False, index=True)

    # Aday bu kurs icin kac saat ders alacak (her sinifa gore degisir)
    ders_sayisi = db.Column(db.Integer, nullable=True)

    # Toplam egitim ucreti (sinav harci HARIC). Adaya ozel — sabit degil.
    fiyat = db.Column(db.Numeric(10, 2), nullable=True, default=0)

    # Egitmen — tenant'in kendi User tablosundan ogretmen rolunde biri.
    # FK koymuyoruz cunku tenant_yonetici de egitmen olabilir; basit FK.
    egitmen_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                           nullable=True)

    notlar = db.Column(db.Text, nullable=True)
    aktif = db.Column(db.Boolean, default=True, nullable=False)

    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow)

    egitmen = db.relationship('User', foreign_keys=[egitmen_id], lazy='joined')

    @property
    def tam_ad(self) -> str:
        return f'{self.ad} {self.soyad}'.strip()

    @property
    def ehliyet_sinifi_str(self) -> str:
        return EHLIYET_SINIF_DICT.get(self.ehliyet_sinifi, self.ehliyet_sinifi)

    def __repr__(self) -> str:
        return f'<Kursiyer {self.tam_ad} {self.ehliyet_sinifi}>'


class KursiyerEhliyet(db.Model):
    """Kursiyerin ek ehliyetleri — bir kursiyer ayni anda birden fazla
    ehliyet sinifi alabilir (orn. B + A2). Kursiyer.ehliyet_sinifi
    'ana' ehliyet olarak korunur (geriye uyumlu); bu tablo ek olanlari
    tutar. Her ehliyet icin ayri fiyat, ders sayisi, egitmen olabilir.
    """
    __tablename__ = 'kursiyer_ehliyetleri'

    id = db.Column(db.Integer, primary_key=True)
    kursiyer_id = db.Column(db.Integer,
                            db.ForeignKey('kursiyerler.id', ondelete='CASCADE'),
                            nullable=False, index=True)
    ehliyet_sinifi = db.Column(db.String(20), nullable=False, index=True)
    ders_sayisi = db.Column(db.Integer, nullable=True)
    fiyat = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    egitmen_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    durum = db.Column(db.String(20), nullable=False, default='aktif')
    # aktif | tamamlandi | iptal
    notlar = db.Column(db.String(200), nullable=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    egitmen = db.relationship('User', foreign_keys=[egitmen_id], lazy='joined')
    kursiyer = db.relationship(
        'Kursiyer',
        backref=db.backref('ek_ehliyetler', lazy='dynamic',
                           cascade='all, delete-orphan',
                           order_by='KursiyerEhliyet.id'),
    )

    __table_args__ = (
        db.UniqueConstraint('kursiyer_id', 'ehliyet_sinifi',
                            name='uq_kursiyer_ehliyet'),
    )

    @property
    def ehliyet_sinifi_str(self) -> str:
        return EHLIYET_SINIF_DICT.get(self.ehliyet_sinifi, self.ehliyet_sinifi)

    def __repr__(self) -> str:
        return f'<KursiyerEhliyet kursiyer={self.kursiyer_id} sinif={self.ehliyet_sinifi}>'


class KursiyerTaksit(db.Model):
    """Kursiyerin egitim ucreti taksitleri — manuel tarihli.

    OgrenciTaksit'ten ayri tablo; OBS'in mevcut taksit akisina
    dokunmuyor.
    """
    __tablename__ = 'kursiyer_taksitleri'

    id = db.Column(db.Integer, primary_key=True)
    kursiyer_id = db.Column(db.Integer,
                            db.ForeignKey('kursiyerler.id', ondelete='CASCADE'),
                            nullable=False, index=True)

    sira = db.Column(db.Integer, nullable=False)  # 1, 2, 3, ...
    vade_tarihi = db.Column(db.Date, nullable=False)
    tutar = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    odendi_mi = db.Column(db.Boolean, default=False, nullable=False)
    odeme_tarihi = db.Column(db.Date, nullable=True)
    odeme_notu = db.Column(db.String(200), nullable=True)

    # Odeme detaylari (Faz 3.A)
    odeme_turu = db.Column(db.String(20), nullable=True)
    # 'nakit' | 'eft' | 'kredi_karti'
    odeyen_ad = db.Column(db.String(150), nullable=True)
    # Kim odedi (kursiyer kendisi, baba, anne vs.)
    teslim_alan_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                                nullable=True)
    # Hangi user (current_user) tahsil etti
    makbuz_no = db.Column(db.String(50), nullable=True, unique=True, index=True)
    # Otomatik uretilir: KSR-YYYYMMDD-NNNN

    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    # Tahsil edildiginde otomatik 'Sürücü Kursu Geliri' kategorisinde
    # GelirGiderKaydi olusur. Geri alinirsa kayit silinir.
    gelir_gider_kayit_id = db.Column(
        db.Integer,
        db.ForeignKey('gelir_gider_kayitlari.id', ondelete='SET NULL'),
        nullable=True,
    )

    teslim_alan = db.relationship('User', foreign_keys=[teslim_alan_id])

    ODEME_TURLERI = [
        ('nakit', 'Nakit'),
        ('eft', 'EFT / Havale'),
        ('kredi_karti', 'Kredi Kartı'),
    ]

    @property
    def odeme_turu_str(self) -> str:
        return dict(self.ODEME_TURLERI).get(self.odeme_turu, '—')

    kursiyer = db.relationship(
        'Kursiyer',
        backref=db.backref('taksitler', lazy='dynamic',
                           cascade='all, delete-orphan',
                           order_by='KursiyerTaksit.sira'),
    )

    def __repr__(self) -> str:
        return (f'<KursiyerTaksit kursiyer={self.kursiyer_id} sira={self.sira} '
                f'vade={self.vade_tarihi} odendi={self.odendi_mi}>')


class SurucuSinavOturumu(db.Model):
    """Bir sinav gunu — birden fazla aday icin ortak.

    Kursumuz ilk yazili+direksiyon harcini odiyor; kalan adaylar 2.
    harci kendileri yatiriyor. Bu oturum o ikinci harc takibini icin.
    """
    __tablename__ = 'surucu_sinav_oturumlari'

    id = db.Column(db.Integer, primary_key=True)
    sinav_tarihi = db.Column(db.Date, nullable=False, index=True)
    sinav_tipi = db.Column(db.String(20), nullable=False)
    # 'yazili' | 'direksiyon'
    notlar = db.Column(db.Text, nullable=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    SINAV_TIPLERI = [('yazili', 'Yazılı Sınav'),
                     ('direksiyon', 'Direksiyon Sınavı')]

    @property
    def sinav_tipi_str(self) -> str:
        return dict(self.SINAV_TIPLERI).get(self.sinav_tipi, self.sinav_tipi)

    def __repr__(self) -> str:
        return f'<SinavOturumu {self.sinav_tarihi} {self.sinav_tipi}>'


class SurucuSinavHarciKaydi(db.Model):
    """Bir sinav oturumunda kalan adayin 2. harc kaydi.

    durum:
        'aday_borclu'   — aday borclu, henuz odenmedi
        'tahsil_edildi' — aday harci yatirdi, kursumuz tahsil etti

    NOT: Bu odemeler kursiyerin egitim ucreti hesabina YANSIMAZ —
    ayri tablo, ayri toplam. Toplam odeme = sum(KursiyerTaksit.odendi)
    + bu satirlar farklı bir kategoride raporlanir.
    """
    __tablename__ = 'surucu_sinav_harci_kayitlari'

    id = db.Column(db.Integer, primary_key=True)
    sinav_oturum_id = db.Column(
        db.Integer,
        db.ForeignKey('surucu_sinav_oturumlari.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    kursiyer_id = db.Column(
        db.Integer, db.ForeignKey('kursiyerler.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )

    ucret = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    durum = db.Column(db.String(20), nullable=False, default='aday_borclu',
                      index=True)
    tahsil_tarihi = db.Column(db.Date, nullable=True)
    notlar = db.Column(db.String(200), nullable=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    # Makbuz alanlari (kursiyer taksiti ile ayni desende)
    odeme_turu = db.Column(db.String(20), nullable=True)
    # 'nakit' | 'eft' | 'kredi_karti'
    odeyen_ad = db.Column(db.String(150), nullable=True)
    teslim_alan_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                                nullable=True)
    makbuz_no = db.Column(db.String(50), nullable=True, unique=True, index=True)
    # Otomatik uretilir: SHR-YYYYMMDD-NNNN

    # Tahsilat yapildiginda otomatik olusturulan muhasebe gelir kaydina
    # link. Tahsilat geri alinirsa ya da kayit silinirse bagli muhasebe
    # kaydi da silinir. ondelete='SET NULL': muhasebe ekraninda elle
    # silinirse de bizimki bozulmaz.
    gelir_gider_kayit_id = db.Column(
        db.Integer,
        db.ForeignKey('gelir_gider_kayitlari.id', ondelete='SET NULL'),
        nullable=True,
    )

    DURUMLAR = [('aday_borclu', 'Aday Borçlu'),
                ('tahsil_edildi', 'Tahsil Edildi')]

    ODEME_TURLERI = [
        ('nakit', 'Nakit'),
        ('eft', 'EFT / Havale'),
        ('kredi_karti', 'Kredi Kartı'),
    ]

    sinav_oturum = db.relationship('SurucuSinavOturumu',
                                    backref=db.backref('harc_kayitlari',
                                                       lazy='dynamic',
                                                       cascade='all, delete-orphan'))
    kursiyer = db.relationship('Kursiyer',
                                backref=db.backref('sinav_harclari',
                                                   lazy='dynamic'))
    teslim_alan = db.relationship('User', foreign_keys=[teslim_alan_id])

    @property
    def durum_str(self) -> str:
        return dict(self.DURUMLAR).get(self.durum, self.durum)

    @property
    def odeme_turu_str(self) -> str:
        return dict(self.ODEME_TURLERI).get(self.odeme_turu, '—')

    def __repr__(self) -> str:
        return (f'<SinavHarciKaydi kursiyer={self.kursiyer_id} '
                f'oturum={self.sinav_oturum_id} durum={self.durum}>')


class KursiyerYonlendirme(db.Model):
    """Kursiyerin baska bir surucu kursuna yonlendirilmesi.

    Kurs kendisinde olmayan bir egitim icin kursiyeri baska bir kursa
    yonlendirir (orn. SRC, psikoteknik). Komisyon karsiligi yapilirsa
    komisyon_alindi_mi=True isaretlendiginde otomatik gelir kaydi
    olusur (mevcut KursiyerTaksit/SinavHarc orüntüsüyle ayni).

    OBS dershanelerinde bu tablo bos kalir; sadece kurum_tipi=
    'surucu_kursu' tenant'larinda menude gorunur.
    """
    __tablename__ = 'kursiyer_yonlendirmeleri'

    id = db.Column(db.Integer, primary_key=True)

    kursiyer_id = db.Column(
        db.Integer,
        db.ForeignKey('kursiyerler.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    # Hangi egitim icin yonlendirildi (SRC5, A2, psikoteknik vs.)
    ehliyet_sinifi = db.Column(db.String(20), nullable=False, index=True)

    # Hedef kurs bilgileri
    hedef_kurs_adi = db.Column(db.String(200), nullable=False)
    hedef_kurs_telefon = db.Column(db.String(20), nullable=True)
    hedef_kurs_yetkili = db.Column(db.String(150), nullable=True)
    # Yetkili kisi (ornegin "Ahmet Bey - mudur")

    # Yonlendirme yapan personel (kayit eden kullanici)
    yonlendiren_id = db.Column(db.Integer,
                                db.ForeignKey('users.id'),
                                nullable=True, index=True)

    yonlendirme_tarihi = db.Column(db.Date, nullable=False, index=True)

    # Komisyon (opsiyonel - bazi kurslar yonlendirme komisyonu verir)
    komisyon_tutari = db.Column(db.Numeric(10, 2), nullable=True, default=0)
    komisyon_alindi_mi = db.Column(db.Boolean, default=False, nullable=False)
    komisyon_tarihi = db.Column(db.Date, nullable=True)

    # Yonlendirme durumu
    durum = db.Column(db.String(20), nullable=False, default='yonlendirildi')
    # 'yonlendirildi' | 'kayit_oldu' | 'tamamlandi' | 'iptal'

    notlar = db.Column(db.Text, nullable=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    # Komisyon tahsil edildiginde otomatik gelir kaydi (set null on delete)
    gelir_gider_kayit_id = db.Column(
        db.Integer,
        db.ForeignKey('gelir_gider_kayitlari.id', ondelete='SET NULL'),
        nullable=True,
    )

    DURUMLAR = [
        ('yonlendirildi', 'Yönlendirildi'),
        ('kayit_oldu',    'Kayıt Oldu'),
        ('tamamlandi',    'Tamamlandı'),
        ('iptal',         'İptal'),
    ]

    kursiyer = db.relationship(
        'Kursiyer',
        backref=db.backref('yonlendirmeler', lazy='dynamic',
                           cascade='all, delete-orphan',
                           order_by='KursiyerYonlendirme.yonlendirme_tarihi.desc()'),
    )
    yonlendiren = db.relationship('User', foreign_keys=[yonlendiren_id],
                                   lazy='joined')

    @property
    def ehliyet_sinifi_str(self) -> str:
        return EHLIYET_SINIF_DICT.get(self.ehliyet_sinifi, self.ehliyet_sinifi)

    @property
    def durum_str(self) -> str:
        return dict(self.DURUMLAR).get(self.durum, self.durum)

    def __repr__(self) -> str:
        return (f'<KursiyerYonlendirme kursiyer={self.kursiyer_id} '
                f'hedef={self.hedef_kurs_adi} durum={self.durum}>')
