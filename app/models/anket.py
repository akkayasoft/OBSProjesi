from datetime import datetime, date
from app.extensions import db


class Anket(db.Model):
    """Online Anket (Survey)"""
    __tablename__ = 'anketler'

    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(300), nullable=False)
    aciklama = db.Column(db.Text, nullable=True)
    olusturan_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hedef_kitle = db.Column(db.String(50), nullable=False, default='tumu')
    # tumu, ogretmen, ogrenci, veli
    baslangic_tarihi = db.Column(db.Date, nullable=False, default=date.today)
    bitis_tarihi = db.Column(db.Date, nullable=False)
    aktif = db.Column(db.Boolean, default=True)
    anonim = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    olusturan = db.relationship('User', backref=db.backref('anketler', lazy='dynamic'))
    sorular = db.relationship('AnketSoru', backref='anket', lazy='dynamic',
                              order_by='AnketSoru.sira',
                              cascade='all, delete-orphan')
    cevaplar = db.relationship('AnketCevap', backref='anket', lazy='dynamic',
                               cascade='all, delete-orphan')

    @property
    def hedef_kitle_str(self):
        kitle_map = {
            'tumu': 'Tumu',
            'ogretmen': 'Ogretmen',
            'ogrenci': 'Ogrenci',
            'veli': 'Veli',
        }
        return kitle_map.get(self.hedef_kitle, self.hedef_kitle)

    @property
    def durum_str(self):
        bugun = date.today()
        if not self.aktif:
            return 'Pasif'
        if bugun < self.baslangic_tarihi:
            return 'Baslamadi'
        if bugun > self.bitis_tarihi:
            return 'Sona Erdi'
        return 'Aktif'

    @property
    def durum_badge(self):
        durum = self.durum_str
        badge_map = {
            'Pasif': 'secondary',
            'Baslamadi': 'warning',
            'Sona Erdi': 'danger',
            'Aktif': 'success',
        }
        return badge_map.get(durum, 'secondary')

    @property
    def katilimci_sayisi(self):
        """Benzersiz katilimci sayisi."""
        return db.session.query(
            db.func.count(db.func.distinct(AnketCevap.kullanici_id))
        ).filter(AnketCevap.anket_id == self.id).scalar() or 0

    def kullanici_cevapladi_mi(self, kullanici_id):
        """Kullanicinin anketi doldurup doldurmadigi."""
        return self.cevaplar.filter_by(kullanici_id=kullanici_id).first() is not None

    def __repr__(self):
        return f'<Anket {self.baslik}>'


class AnketSoru(db.Model):
    """Anket Sorusu (Survey Question)"""
    __tablename__ = 'anket_sorulari'

    id = db.Column(db.Integer, primary_key=True)
    anket_id = db.Column(db.Integer, db.ForeignKey('anketler.id'), nullable=False)
    soru_metni = db.Column(db.Text, nullable=False)
    soru_tipi = db.Column(db.String(50), nullable=False, default='coktan_secmeli')
    # coktan_secmeli, acik_uclu, derecelendirme, evet_hayir
    secenekler = db.Column(db.Text, nullable=True)  # JSON string for choices
    sira = db.Column(db.Integer, nullable=False, default=0)
    zorunlu = db.Column(db.Boolean, default=True)

    soru_cevaplari = db.relationship('AnketCevap', backref='soru', lazy='dynamic',
                                     cascade='all, delete-orphan')

    @property
    def soru_tipi_str(self):
        tip_map = {
            'coktan_secmeli': 'Coktan Secmeli',
            'acik_uclu': 'Acik Uclu',
            'derecelendirme': 'Derecelendirme (1-5)',
            'evet_hayir': 'Evet / Hayir',
        }
        return tip_map.get(self.soru_tipi, self.soru_tipi)

    @property
    def secenekler_listesi(self):
        """JSON string secenekleri listeye cevirir."""
        if not self.secenekler:
            return []
        import json
        try:
            return json.loads(self.secenekler)
        except (json.JSONDecodeError, TypeError):
            return []

    def __repr__(self):
        return f'<AnketSoru {self.id} - {self.soru_tipi}>'


class AnketCevap(db.Model):
    """Anket Cevabi (Survey Answer)"""
    __tablename__ = 'anket_cevaplari'

    id = db.Column(db.Integer, primary_key=True)
    anket_id = db.Column(db.Integer, db.ForeignKey('anketler.id'), nullable=False)
    soru_id = db.Column(db.Integer, db.ForeignKey('anket_sorulari.id'), nullable=False)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    cevap = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    kullanici = db.relationship('User', backref=db.backref('anket_cevaplari', lazy='dynamic'))

    def __repr__(self):
        return f'<AnketCevap {self.id}>'
