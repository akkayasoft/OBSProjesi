from datetime import datetime, date
from app.extensions import db


class GelirGiderKategorisi(db.Model):
    __tablename__ = 'gelir_gider_kategorileri'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)
    tur = db.Column(db.String(10), nullable=False)  # 'gelir' veya 'gider'
    ust_kategori_id = db.Column(db.Integer, db.ForeignKey('gelir_gider_kategorileri.id'), nullable=True)
    aktif = db.Column(db.Boolean, default=True)

    ust_kategori = db.relationship('GelirGiderKategorisi', remote_side=[id], backref='alt_kategoriler')
    kayitlar = db.relationship('GelirGiderKaydi', backref='kategori', lazy='dynamic')

    def __repr__(self):
        return f'<Kategori {self.ad} ({self.tur})>'


class GelirGiderKaydi(db.Model):
    __tablename__ = 'gelir_gider_kayitlari'

    id = db.Column(db.Integer, primary_key=True)
    kategori_id = db.Column(db.Integer, db.ForeignKey('gelir_gider_kategorileri.id'), nullable=False)
    tur = db.Column(db.String(10), nullable=False)  # 'gelir' veya 'gider'
    tutar = db.Column(db.Numeric(12, 2), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    belge_no = db.Column(db.String(50), nullable=True)
    banka_hesap_id = db.Column(db.Integer, db.ForeignKey('banka_hesaplari.id'), nullable=True)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    olusturan = db.relationship('User', backref='gelir_gider_kayitlari')
    banka_hesap = db.relationship('BankaHesabi', backref='gelir_gider_kayitlari')

    def __repr__(self):
        return f'<GelirGider {self.tur} {self.tutar}>'


class Ogrenci(db.Model):
    __tablename__ = 'ogrenciler'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, unique=True)
    ogrenci_no = db.Column(db.String(20), unique=True, nullable=False)
    tc_kimlik = db.Column(db.String(11), nullable=True)
    ad = db.Column(db.String(100), nullable=False)
    soyad = db.Column(db.String(100), nullable=False)
    cinsiyet = db.Column(db.String(10), nullable=True)  # erkek, kadin
    dogum_tarihi = db.Column(db.Date, nullable=True)
    dogum_yeri = db.Column(db.String(100), nullable=True)
    sinif = db.Column(db.String(20), nullable=True)
    veli_ad = db.Column(db.String(100), nullable=True)
    veli_telefon = db.Column(db.String(20), nullable=True)
    telefon = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    adres = db.Column(db.Text, nullable=True)
    kan_grubu = db.Column(db.String(10), nullable=True)
    aktif = db.Column(db.Boolean, default=True)
    kayit_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('ogrenci', uselist=False))
    odeme_planlari = db.relationship('OdemePlani', backref='ogrenci', lazy='dynamic')

    @property
    def tam_ad(self):
        return f"{self.ad} {self.soyad}"

    @property
    def toplam_borc(self):
        toplam = 0
        for plan in self.odeme_planlari:
            # Kapatilmis/iptal edilmis planlar borca dahil edilmez
            if plan.durum in ('kapali', 'iptal'):
                continue
            for taksit in plan.taksitler:
                if taksit.durum == 'iptal':
                    continue
                toplam += float(taksit.tutar) - float(taksit.odenen_tutar)
        return max(toplam, 0)

    def __repr__(self):
        return f'<Ogrenci {self.ogrenci_no} {self.ad} {self.soyad}>'


class OdemePlani(db.Model):
    __tablename__ = 'odeme_planlari'

    id = db.Column(db.Integer, primary_key=True)
    ogrenci_id = db.Column(db.Integer, db.ForeignKey('ogrenciler.id'), nullable=False)
    donem = db.Column(db.String(20), nullable=False)
    toplam_tutar = db.Column(db.Numeric(12, 2), nullable=False)
    indirim_tutar = db.Column(db.Numeric(12, 2), default=0)
    indirim_aciklama = db.Column(db.String(200), nullable=True)
    taksit_sayisi = db.Column(db.Integer, nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    durum = db.Column(db.String(20), default='aktif')  # aktif, kapali, iptal
    kapanma_tarihi = db.Column(db.DateTime, nullable=True)
    kapanma_nedeni = db.Column(db.String(200), nullable=True)
    onceki_plan_id = db.Column(db.Integer, db.ForeignKey('odeme_planlari.id'), nullable=True)

    onceki_plan = db.relationship('OdemePlani', remote_side=[id], backref='yeni_plan')

    taksitler = db.relationship('Taksit', backref='odeme_plani', lazy='dynamic',
                                order_by='Taksit.taksit_no')

    @property
    def net_tutar(self):
        return float(self.toplam_tutar) - float(self.indirim_tutar or 0)

    @property
    def odenen_toplam(self):
        return sum(float(t.odenen_tutar) for t in self.taksitler)

    @property
    def kalan_borc(self):
        return self.net_tutar - self.odenen_toplam

    def __repr__(self):
        return f'<OdemePlani {self.donem} {self.toplam_tutar}>'


class Taksit(db.Model):
    __tablename__ = 'taksitler'

    id = db.Column(db.Integer, primary_key=True)
    odeme_plani_id = db.Column(db.Integer, db.ForeignKey('odeme_planlari.id'), nullable=False)
    taksit_no = db.Column(db.Integer, nullable=False)
    tutar = db.Column(db.Numeric(12, 2), nullable=False)
    vade_tarihi = db.Column(db.Date, nullable=False)
    orjinal_vade_tarihi = db.Column(db.Date, nullable=True)
    odenen_tutar = db.Column(db.Numeric(12, 2), default=0)
    odeme_tarihi = db.Column(db.Date, nullable=True)
    durum = db.Column(db.String(20), default='beklemede')
    # beklemede, odendi, gecikti, kismi_odendi, ertelendi
    erteleme_notu = db.Column(db.String(200), nullable=True)

    odemeler = db.relationship('Odeme', backref='taksit', lazy='dynamic')

    @property
    def kalan(self):
        return float(self.tutar) - float(self.odenen_tutar)

    @property
    def gecikti_mi(self):
        if self.durum == 'odendi':
            return False
        return date.today() > self.vade_tarihi

    def durum_guncelle(self):
        if self.durum == 'iptal':
            return
        if float(self.tutar) == 0:
            # Tum tutar odendi veya iptal; koruma
            self.durum = 'odendi' if float(self.odenen_tutar) > 0 else 'iptal'
            return
        if float(self.odenen_tutar) >= float(self.tutar):
            self.durum = 'odendi'
        elif float(self.odenen_tutar) > 0:
            self.durum = 'kismi_odendi'
        elif date.today() > self.vade_tarihi:
            self.durum = 'gecikti'
        else:
            self.durum = 'beklemede'

    def __repr__(self):
        return f'<Taksit {self.taksit_no} {self.tutar}>'


class Odeme(db.Model):
    __tablename__ = 'odemeler'

    id = db.Column(db.Integer, primary_key=True)
    taksit_id = db.Column(db.Integer, db.ForeignKey('taksitler.id'), nullable=False)
    tutar = db.Column(db.Numeric(12, 2), nullable=False)
    odeme_turu = db.Column(db.String(20), nullable=False)  # nakit, havale, kredi_karti, eft
    banka_hesap_id = db.Column(db.Integer, db.ForeignKey('banka_hesaplari.id'), nullable=True)
    makbuz_no = db.Column(db.String(50), unique=True)
    aciklama = db.Column(db.Text, nullable=True)
    tarih = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Iptal / iade bilgileri
    iptal_edildi = db.Column(db.Boolean, default=False)
    iptal_tarihi = db.Column(db.DateTime, nullable=True)
    iptal_nedeni = db.Column(db.String(200), nullable=True)
    iptal_eden_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    olusturan = db.relationship('User', foreign_keys=[olusturan_id], backref='odemeler')
    iptal_eden = db.relationship('User', foreign_keys=[iptal_eden_id])
    banka_hesap = db.relationship('BankaHesabi', backref='odemeler')

    def __repr__(self):
        return f'<Odeme {self.makbuz_no} {self.tutar}>'


class Personel(db.Model):
    __tablename__ = 'personeller'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, unique=True)
    sicil_no = db.Column(db.String(20), unique=True, nullable=False)
    ad = db.Column(db.String(100), nullable=False)
    soyad = db.Column(db.String(100), nullable=False)
    pozisyon = db.Column(db.String(100), nullable=True)
    maas = db.Column(db.Numeric(12, 2), nullable=True)
    aktif = db.Column(db.Boolean, default=True)

    # Kişisel Bilgiler
    tc_kimlik = db.Column(db.String(11), nullable=True)
    cinsiyet = db.Column(db.String(10), nullable=True)
    dogum_tarihi = db.Column(db.Date, nullable=True)
    telefon = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    adres = db.Column(db.Text, nullable=True)

    # İş Bilgileri
    departman = db.Column(db.String(100), nullable=True)
    ise_baslama_tarihi = db.Column(db.Date, nullable=True)
    ise_bitis_tarihi = db.Column(db.Date, nullable=True)
    calisma_turu = db.Column(db.String(20), default='tam_zamanli')

    user = db.relationship('User', backref=db.backref('personel', uselist=False))
    odeme_kayitlari = db.relationship('PersonelOdemeKaydi', backref='personel', lazy='dynamic')
    izinler = db.relationship('PersonelIzin', backref='personel', lazy='dynamic')

    @property
    def tam_ad(self):
        return f"{self.ad} {self.soyad}"

    @property
    def calisma_turu_str(self):
        turu_map = {
            'tam_zamanli': 'Tam Zamanlı',
            'yari_zamanli': 'Yarı Zamanlı',
            'sozlesmeli': 'Sözleşmeli',
        }
        return turu_map.get(self.calisma_turu, self.calisma_turu)

    def __repr__(self):
        return f'<Personel {self.sicil_no} {self.ad} {self.soyad}>'


class PersonelOdemeKaydi(db.Model):
    __tablename__ = 'personel_odeme_kayitlari'

    id = db.Column(db.Integer, primary_key=True)
    personel_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=False)
    donem = db.Column(db.String(20), nullable=False)
    tutar = db.Column(db.Numeric(12, 2), nullable=False)
    odeme_turu = db.Column(db.String(20), nullable=False)
    banka_hesap_id = db.Column(db.Integer, db.ForeignKey('banka_hesaplari.id'), nullable=True)
    aciklama = db.Column(db.Text, nullable=True)
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    olusturan = db.relationship('User', backref='personel_odeme_kayitlari')
    banka_hesap = db.relationship('BankaHesabi', backref='personel_odeme_kayitlari')

    def __repr__(self):
        return f'<PersonelOdeme {self.donem} {self.tutar}>'


class BankaHesabi(db.Model):
    __tablename__ = 'banka_hesaplari'

    id = db.Column(db.Integer, primary_key=True)
    banka_adi = db.Column(db.String(100), nullable=False)
    hesap_adi = db.Column(db.String(100), nullable=False)
    iban = db.Column(db.String(34), nullable=True)
    hesap_no = db.Column(db.String(30), nullable=True)
    bakiye = db.Column(db.Numeric(12, 2), default=0)
    para_birimi = db.Column(db.String(5), default='TRY')
    aktif = db.Column(db.Boolean, default=True)

    hareketler = db.relationship('BankaHareketi',
                                 backref='banka_hesap',
                                 lazy='dynamic',
                                 foreign_keys='BankaHareketi.banka_hesap_id')

    def __repr__(self):
        return f'<BankaHesabi {self.banka_adi} {self.hesap_adi}>'


class BankaHareketi(db.Model):
    __tablename__ = 'banka_hareketleri'

    id = db.Column(db.Integer, primary_key=True)
    banka_hesap_id = db.Column(db.Integer, db.ForeignKey('banka_hesaplari.id'), nullable=False)
    tur = db.Column(db.String(10), nullable=False)  # giris, cikis, transfer
    tutar = db.Column(db.Numeric(12, 2), nullable=False)
    karsi_hesap_id = db.Column(db.Integer, db.ForeignKey('banka_hesaplari.id'), nullable=True)
    aciklama = db.Column(db.Text, nullable=True)
    tarih = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    karsi_hesap = db.relationship('BankaHesabi', foreign_keys=[karsi_hesap_id])

    def __repr__(self):
        return f'<BankaHareketi {self.tur} {self.tutar}>'
