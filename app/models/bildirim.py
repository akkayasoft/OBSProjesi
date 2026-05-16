from datetime import datetime
from app.extensions import db


class Bildirim(db.Model):
    __tablename__ = 'bildirimler'

    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    baslik = db.Column(db.String(200), nullable=False)
    mesaj = db.Column(db.Text, nullable=False)
    tur = db.Column(db.String(20), nullable=False, default='bilgi')  # bilgi/uyari/basari/hata
    kategori = db.Column(db.String(20), nullable=False, default='sistem')  # mesaj/not/devamsizlik/duyuru/sinav/odeme/sistem/diger
    link = db.Column(db.String(500), nullable=True)
    okundu = db.Column(db.Boolean, default=False)
    okunma_tarihi = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    kullanici = db.relationship('User', backref=db.backref('bildirimler', lazy='dynamic'))

    @classmethod
    def olustur(cls, kullanici_id, baslik, mesaj, tur='bilgi', kategori='sistem', link=None):
        bildirim = cls(
            kullanici_id=kullanici_id,
            baslik=baslik,
            mesaj=mesaj,
            tur=tur,
            kategori=kategori,
            link=link
        )
        db.session.add(bildirim)
        db.session.commit()
        return bildirim

    @classmethod
    def toplu_olustur(cls, kullanici_ids, baslik, mesaj, tur='bilgi', kategori='sistem', link=None):
        for kid in kullanici_ids:
            db.session.add(cls(
                kullanici_id=kid,
                baslik=baslik,
                mesaj=mesaj,
                tur=tur,
                kategori=kategori,
                link=link
            ))
        db.session.commit()

    @classmethod
    def okunmamis_sayisi(cls, kullanici_id):
        return cls.query.filter_by(kullanici_id=kullanici_id, okundu=False).count()

    def __repr__(self):
        return f'<Bildirim {self.id} - {self.baslik}>'


class PushAbonelik(db.Model):
    """Web Push (VAPID) abonelik kayitlari.

    Her cihaz/tarayici icin ayri bir endpoint olur. Ayni kullanicinin birden
    fazla kaydi olabilir (telefon + bilgisayar). endpoint alani benzersizdir.
    """
    __tablename__ = 'push_abonelikler'

    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                             nullable=False, index=True)
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    user_agent = db.Column(db.String(500), nullable=True)
    aktif = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    son_kullanim = db.Column(db.DateTime, default=datetime.utcnow)

    kullanici = db.relationship('User',
                                backref=db.backref('push_abonelikleri',
                                                   lazy='dynamic',
                                                   cascade='all, delete-orphan'))

    def subscription_info(self) -> dict:
        """pywebpush'un bekledigi formata cevir."""
        return {
            'endpoint': self.endpoint,
            'keys': {
                'p256dh': self.p256dh,
                'auth': self.auth,
            }
        }

    def __repr__(self):
        return f'<PushAbonelik {self.id} user={self.kullanici_id}>'


class CihazTokeni(db.Model):
    """Mobil uygulama (Flutter) FCM push token kayitlari.

    Her cihaz icin bir FCM token. Ayni kullanicinin birden fazla
    cihazi olabilir. token benzersizdir; ayni token baska kullaniciya
    gecerse uzerine yazilir (cihaz el degistirmis olabilir).
    """
    __tablename__ = 'cihaz_tokenleri'

    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                             nullable=False, index=True)
    token = db.Column(db.String(512), nullable=False, unique=True)
    platform = db.Column(db.String(20), nullable=True)  # android / ios
    aktif = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    guncelleme_tarihi = db.Column(db.DateTime, default=datetime.utcnow,
                                  onupdate=datetime.utcnow)

    kullanici = db.relationship('User',
                                backref=db.backref('cihaz_tokenleri',
                                                   lazy='dynamic',
                                                   cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<CihazTokeni {self.id} user={self.kullanici_id}>'


class BildirimSablonu(db.Model):
    """Bildirim (push + in-app) sablonlari.

    Placeholder'lar: {ad}, {soyad}, {ogrenci_no}, {sinif}, {sube},
                     {tutar}, {vade}, {veli_ad}, {veli_soyad}, {kurum}

    kategori: genel, dogum_gunu, taksit_hatirlatma, veli_gorusme, toplanti,
              tebrik, diger
    """
    __tablename__ = 'bildirim_sablonlari'

    id = db.Column(db.Integer, primary_key=True)
    ad = db.Column(db.String(100), nullable=False)  # kisa etiket
    baslik = db.Column(db.String(200), nullable=False)
    mesaj = db.Column(db.Text, nullable=False)
    kategori = db.Column(db.String(30), nullable=False, default='genel')
    link = db.Column(db.String(500), nullable=True)
    sistem = db.Column(db.Boolean, default=False)  # seed edilmis sistem sablonu
    aktif = db.Column(db.Boolean, default=True, nullable=False)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow,
                           onupdate=datetime.utcnow)

    olusturan = db.relationship('User',
                                backref=db.backref('bildirim_sablonlari',
                                                   lazy='dynamic'))

    KATEGORILER = [
        ('genel', 'Genel'),
        ('dogum_gunu', 'Dogum Gunu'),
        ('taksit_hatirlatma', 'Taksit Hatirlatma'),
        ('veli_gorusme', 'Veli Gorusme'),
        ('toplanti', 'Toplanti'),
        ('tebrik', 'Tebrik'),
        ('diger', 'Diger'),
    ]

    @property
    def kategori_str(self):
        return dict(self.KATEGORILER).get(self.kategori, self.kategori)

    @property
    def kategori_badge(self):
        badge_map = {
            'genel': 'secondary',
            'dogum_gunu': 'warning',
            'taksit_hatirlatma': 'info',
            'veli_gorusme': 'primary',
            'toplanti': 'success',
            'tebrik': 'warning',
            'diger': 'dark',
        }
        return badge_map.get(self.kategori, 'secondary')

    def __repr__(self):
        return f'<BildirimSablonu {self.ad}>'


class BildirimGonderim(db.Model):
    """Ozel bildirim gonderim gecmisi (log/audit).

    Her 'gonder' islemi tek kayit. Alicilar sayilar halinde tutulur.
    """
    __tablename__ = 'bildirim_gonderimleri'

    id = db.Column(db.Integer, primary_key=True)
    gonderen_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sablon_id = db.Column(db.Integer, db.ForeignKey('bildirim_sablonlari.id'),
                          nullable=True)
    baslik = db.Column(db.String(200), nullable=False)
    mesaj = db.Column(db.Text, nullable=False)
    kategori = db.Column(db.String(30), nullable=False, default='genel')
    link = db.Column(db.String(500), nullable=True)
    alici_sayisi = db.Column(db.Integer, default=0, nullable=False)
    push_basarili = db.Column(db.Integer, default=0, nullable=False)
    kaynak = db.Column(db.String(30), default='manuel', nullable=False)
    # manuel, dogum_gunu_cron, muhasebe_hatirlat
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    gonderen = db.relationship('User',
                               backref=db.backref('bildirim_gonderimleri',
                                                  lazy='dynamic'))
    sablon = db.relationship('BildirimSablonu',
                             backref=db.backref('gonderimler', lazy='dynamic'))

    def __repr__(self):
        return f'<BildirimGonderim {self.id} ({self.alici_sayisi} alici)>'
