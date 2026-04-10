from datetime import datetime
from app.extensions import db


class RolModulIzin(db.Model):
    """Rol bazlı modül erişim izinleri"""
    __tablename__ = 'rol_modul_izinleri'

    id = db.Column(db.Integer, primary_key=True)
    rol = db.Column(db.String(20), nullable=False)
    modul_key = db.Column(db.String(50), nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('rol', 'modul_key', name='uq_rol_modul'),
    )

    # Tüm modül tanımları (key -> Türkçe label)
    MODULLER = {
        'ogretmen_portal': 'Öğretmen Portalı',
        'ogrenci_portal': 'Öğrenci Portalı',
        'kullanici': 'Kullanıcı Yönetimi',
        'kurum': 'Kurum Yönetimi',
        'kayit': 'Kayıt Yönetimi',
        'muhasebe': 'Muhasebe',
        'devamsizlik': 'Devamsızlık',
        'personel': 'Personel Yönetimi',
        'ders_dagitimi': 'Ders Dağıtımı',
        'not_defteri': 'Not Defteri',
        'odev_takip': 'Ödev Takip',
        'davranis': 'Davranış Değerlendirme',
        'karne': 'Karne / Transkript',
        'etut': 'Etüt Yönetimi',
        'sinav_oturum': 'Sınav Oturum Yönetimi',
        'duyurular': 'Duyurular',
        'rehberlik': 'Rehberlik',
        'saglik': 'Sağlık',
        'iletisim': 'İletişim',
        'online_sinav': 'Online Sınav',
        'kulupler': 'Kulüpler',
        'ortak_sinav': 'Ortak Sınavlar',
        'anket': 'Online Anket',
        'servis': 'Öğrenci Servisi',
        'kantin': 'Kantin / Yemekhane',
        'kutuphane': 'Kütüphane',
        'envanter': 'Envanter / Demirbaş',
        'yurt': 'Yurt / Pansiyon',
        'ders_programi': 'Ders Programı',
        'raporlama': 'Raporlama',
        'denetim': 'Denetim Kaydı',
        'belge': 'Belge Yönetimi',
        'ayarlar': 'Sistem Ayarları',
        'bildirim': 'Bildirimler',
    }

    ROLLER = {
        'admin': 'Yönetici',
        'ogretmen': 'Öğretmen',
        'muhasebeci': 'Muhasebeci',
        'veli': 'Veli',
        'ogrenci': 'Öğrenci',
    }

    @classmethod
    def izin_var_mi(cls, rol, modul_key):
        """Belirtilen rolün belirtilen modüle erişimi var mı?"""
        if rol == 'admin':
            # Admin her zaman tüm modüllere erişir (devre dışı bırakılabilir)
            izin = cls.query.filter_by(rol='admin', modul_key=modul_key).first()
            if izin is None:
                return True  # Varsayılan: admin erişebilir
            return izin.aktif
        izin = cls.query.filter_by(rol=rol, modul_key=modul_key).first()
        if izin is None:
            return False  # Varsayılan: kayıt yoksa erişim yok
        return izin.aktif

    @classmethod
    def rol_izinleri(cls, rol):
        """Bir rolün erişebildiği modül key'lerini döndür"""
        izinler = cls.query.filter_by(rol=rol, aktif=True).all()
        return {i.modul_key for i in izinler}

    @classmethod
    def varsayilan_izinleri_olustur(cls):
        """Varsayılan izinleri oluştur (mevcut hardcoded yapıdan)"""
        varsayilan = {
            'admin': list(cls.MODULLER.keys()),
            'ogretmen': [
                'ogretmen_portal', 'devamsizlik', 'ders_dagitimi', 'not_defteri',
                'odev_takip', 'davranis', 'karne', 'etut', 'sinav_oturum',
                'duyurular', 'rehberlik', 'online_sinav', 'kulupler',
                'ortak_sinav', 'anket', 'iletisim', 'ders_programi', 'bildirim',
            ],
            'muhasebeci': ['muhasebe', 'kayit', 'duyurular', 'iletisim', 'bildirim'],
            'veli': ['ogrenci_portal', 'duyurular', 'anket', 'iletisim', 'bildirim'],
            'ogrenci': ['ogrenci_portal', 'duyurular', 'anket', 'iletisim', 'online_sinav', 'bildirim'],
        }
        for rol, moduller in varsayilan.items():
            for modul_key in cls.MODULLER.keys():
                mevcut = cls.query.filter_by(rol=rol, modul_key=modul_key).first()
                if not mevcut:
                    db.session.add(cls(
                        rol=rol,
                        modul_key=modul_key,
                        aktif=(modul_key in moduller),
                    ))
        db.session.commit()

    def __repr__(self):
        return f'<RolModulIzin {self.rol}:{self.modul_key}={self.aktif}>'


class SistemAyar(db.Model):
    __tablename__ = 'sistem_ayarlari'

    id = db.Column(db.Integer, primary_key=True)
    anahtar = db.Column(db.String(100), unique=True, nullable=False)
    deger = db.Column(db.Text, nullable=True)
    aciklama = db.Column(db.String(300), nullable=True)
    kategori = db.Column(db.String(20), nullable=False, default='genel')
    tur = db.Column(db.String(20), nullable=False, default='text')
    varsayilan = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    KATEGORI_CHOICES = [
        ('genel', 'Genel'),
        ('akademik', 'Akademik'),
        ('muhasebe', 'Muhasebe'),
        ('iletisim', 'Iletisim'),
        ('guvenlik', 'Guvenlik'),
    ]

    TUR_CHOICES = [
        ('text', 'Metin'),
        ('number', 'Sayi'),
        ('boolean', 'Evet/Hayir'),
        ('select', 'Secim'),
        ('email', 'E-posta'),
        ('url', 'URL'),
    ]

    @classmethod
    def get(cls, anahtar, varsayilan=None):
        ayar = cls.query.filter_by(anahtar=anahtar).first()
        return ayar.deger if ayar else varsayilan

    @classmethod
    def set(cls, anahtar, deger, user_id=None):
        ayar = cls.query.filter_by(anahtar=anahtar).first()
        if ayar:
            ayar.deger = str(deger)
            ayar.updated_by = user_id
        # don't create new ones from here
        db.session.commit()

    @property
    def kategori_str(self):
        kat_map = dict(self.KATEGORI_CHOICES)
        return kat_map.get(self.kategori, self.kategori)

    @property
    def tur_str(self):
        tur_map = dict(self.TUR_CHOICES)
        return tur_map.get(self.tur, self.tur)

    def __repr__(self):
        return f'<SistemAyar {self.anahtar}={self.deger}>'
