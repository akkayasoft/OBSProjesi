"""Surucu kursu modulu modelleri.

Sadece kurum_tipi='surucu_kursu' olan tenant'lar tarafindan kullanilir.
Mevcut OBS modellerinden (Ogrenci, OgrenciTaksit) bagimsiz — dershane
tenant'larini etkilemez.

Tablolar her tenant DB'sinde olusturulur (db.metadata.create_all
calistiginda) ama dershane tenant'larinda bos kalir, hicbir kod o
tablolara dokunmaz.
"""
import calendar
from datetime import date, datetime
from app.extensions import db


AY_ADLARI = [
    'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
    'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
]


class Donem(db.Model):
    """Surucu kursu donemleri (her ay bir donem).

    Kursiyerler kayit_tarihi'ne gore otomatik bir doneme atanir.
    Donem bazli odeme/kursiyer takibi icin kullanilir.
    """
    __tablename__ = 'surucu_donemler'

    id = db.Column(db.Integer, primary_key=True)
    yil = db.Column(db.Integer, nullable=False, index=True)
    ay = db.Column(db.Integer, nullable=False, index=True)  # 1-12
    ad = db.Column(db.String(50), nullable=False)
    # Otomatik: 'Mayıs 2026'
    baslangic_tarihi = db.Column(db.Date, nullable=False)
    bitis_tarihi = db.Column(db.Date, nullable=False)
    durum = db.Column(db.String(20), nullable=False, default='aktif',
                      index=True)
    # 'aktif' | 'kapali'
    aciklama = db.Column(db.Text, nullable=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('yil', 'ay', name='uq_surucu_donem_yil_ay'),
    )

    @classmethod
    def from_yil_ay(cls, yil: int, ay: int) -> 'Donem':
        """Yil+ay icin yeni bir Donem nesnesi olustur (DB'ye eklenmemis).

        ad ve tarihler otomatik hesaplanir.
        """
        ad = f'{AY_ADLARI[ay - 1]} {yil}'
        baslangic = date(yil, ay, 1)
        son_gun = calendar.monthrange(yil, ay)[1]
        bitis = date(yil, ay, son_gun)
        return cls(
            yil=yil, ay=ay, ad=ad,
            baslangic_tarihi=baslangic, bitis_tarihi=bitis,
            durum='aktif',
        )

    @property
    def kisa_ad(self) -> str:
        """'Mayıs 2026' yerine '05/2026' kisa formati."""
        return f'{self.ay:02d}/{self.yil}'

    def __repr__(self) -> str:
        return f'<Donem {self.ad}>'


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
    tc_kimlik = db.Column(db.String(11), nullable=True, index=True)
    telefon = db.Column(db.String(40), nullable=True, index=True)

    # Kayit donemi: ay/yil bazli (form'da date input ama gun ignore edilir)
    kayit_tarihi = db.Column(db.Date, nullable=False, default=datetime.utcnow)

    # NOT: Eskiden zorunluydu; yeni akista kursiyer kaydedilirken
    # ehliyet sinifi alinmiyor — kayit sonrasi KursiyerEhliyet uzerinden
    # ehliyetler eklenir. Geriye uyumluluk icin nullable; mevcut
    # kursiyerlerde dolu kalir.
    ehliyet_sinifi = db.Column(db.String(20), nullable=True, index=True)

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

    # Donem (ay bazli grup) — kayit_tarihi'ne gore otomatik atanir
    donem_id = db.Column(db.Integer,
                          db.ForeignKey('surucu_donemler.id',
                                        ondelete='SET NULL'),
                          nullable=True, index=True)

    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                            onupdate=datetime.utcnow)

    egitmen = db.relationship('User', foreign_keys=[egitmen_id], lazy='joined')
    donem = db.relationship('Donem',
                             backref=db.backref('kursiyerler',
                                                lazy='dynamic',
                                                order_by='Kursiyer.ad'))

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
    # Otomatik taksit sayisi - ehliyet eklenirken fiyat bu sayiya
    # bolunup N tane KursiyerTaksit olusturulur. 1 = tek taksit (default).
    taksit_sayisi = db.Column(db.Integer, nullable=True, default=1)
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

    # Bu taksit hangi ehliyet kaydindan otomatik olusturuldu?
    # NULL ise eski/manuel taksit (uzaki taksit plani gibi). Linkli
    # taksitler ehliyet ekle/duzenle/sil sirasinda otomatik senkron edilir.
    kursiyer_ehliyet_id = db.Column(
        db.Integer,
        db.ForeignKey('kursiyer_ehliyetleri.id', ondelete='SET NULL'),
        nullable=True, index=True,
    )

    # Tahsil edildiginde otomatik 'Sürücü Kursu Geliri' kategorisinde
    # GelirGiderKaydi olusur. Geri alinirsa kayit silinir.
    gelir_gider_kayit_id = db.Column(
        db.Integer,
        db.ForeignKey('gelir_gider_kayitlari.id', ondelete='SET NULL'),
        nullable=True,
    )

    teslim_alan = db.relationship('User', foreign_keys=[teslim_alan_id])
    kursiyer_ehliyet = db.relationship('KursiyerEhliyet',
                                        foreign_keys=[kursiyer_ehliyet_id])

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


class KomisyonOdemesi(db.Model):
    """Baska kurslarin BIZE yonlendirdigi kursiyerler icin BIZIM
    odeyecegimiz komisyon (yon='gelen').

    KursiyerYonlendirme'nin tersi: yonlendirme modulu bizim
    gonderdiklerimiz (gelir), bu modul bize gelenler (gider).

    Kursiyer FK opsiyonel - bize yonlendirilen kisi sistem'e kayit
    olabilir veya olmayabilir. Olmamissa kursiyer_adi serbest metin
    olarak girilir.

    Komisyon odendi olarak isaretlendiginde otomatik 'Yonlendirme
    Komisyon Gideri' kategorisinde GelirGiderKaydi (tur='gider')
    olusur. Iptal edilince gider kaydi silinir.
    """
    __tablename__ = 'surucu_komisyon_odemeleri'

    id = db.Column(db.Integer, primary_key=True)

    # Hangi kursiyer icin (sistemimizde varsa FK, yoksa serbest metin)
    kursiyer_id = db.Column(
        db.Integer,
        db.ForeignKey('kursiyerler.id', ondelete='SET NULL'),
        nullable=True, index=True,
    )
    kursiyer_adi = db.Column(db.String(150), nullable=False)
    # FK varsa kursiyer.tam_ad ile esit, yoksa elle girilir
    kursiyer_telefon = db.Column(db.String(40), nullable=True)
    ehliyet_sinifi = db.Column(db.String(20), nullable=True)
    # Hangi egitim icin yonlendirildi (opsiyonel)

    # Kaynak (yonlendiren) kurs bilgileri
    kaynak_kurs_adi = db.Column(db.String(200), nullable=False)
    kaynak_kurs_yetkili = db.Column(db.String(150), nullable=True)
    kaynak_kurs_telefon = db.Column(db.String(40), nullable=True)

    # Bizim taraftan kaydeden personel
    kaydeden_id = db.Column(db.Integer,
                             db.ForeignKey('users.id'),
                             nullable=True, index=True)

    yonlendirme_tarihi = db.Column(db.Date, nullable=False, index=True)

    komisyon_tutari = db.Column(db.Numeric(10, 2),
                                 nullable=False, default=0)
    odendi_mi = db.Column(db.Boolean, default=False, nullable=False,
                           index=True)
    odeme_tarihi = db.Column(db.Date, nullable=True)

    aciklama = db.Column(db.Text, nullable=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    # Komisyon odendiginde otomatik gider kaydi linki
    gelir_gider_kayit_id = db.Column(
        db.Integer,
        db.ForeignKey('gelir_gider_kayitlari.id', ondelete='SET NULL'),
        nullable=True,
    )

    kursiyer = db.relationship('Kursiyer', foreign_keys=[kursiyer_id])
    kaydeden = db.relationship('User', foreign_keys=[kaydeden_id],
                                lazy='joined')

    @property
    def ehliyet_sinifi_str(self) -> str:
        if not self.ehliyet_sinifi:
            return '—'
        return EHLIYET_SINIF_DICT.get(self.ehliyet_sinifi, self.ehliyet_sinifi)

    def __repr__(self) -> str:
        return (f'<KomisyonOdemesi kursiyer={self.kursiyer_adi!r} '
                f'kaynak={self.kaynak_kurs_adi!r} '
                f'tutar={self.komisyon_tutari} odendi={self.odendi_mi}>')
