from datetime import datetime, date
from app.extensions import db


class Demirbas(db.Model):
    __tablename__ = 'demirbaslar'

    id = db.Column(db.Integer, primary_key=True)
    barkod = db.Column(db.String(50), unique=True, nullable=True)
    ad = db.Column(db.String(300), nullable=False)
    kategori = db.Column(db.String(50), nullable=False)
    marka = db.Column(db.String(100), nullable=True)
    model_adi = db.Column(db.String(100), nullable=True)
    seri_no = db.Column(db.String(100), nullable=True)
    edinme_tarihi = db.Column(db.Date, nullable=True)
    edinme_fiyati = db.Column(db.Float, nullable=True)
    konum = db.Column(db.String(200), nullable=False)
    sorumlu_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=True)
    durum = db.Column(db.String(20), nullable=False, default='aktif')
    aciklama = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sorumlu = db.relationship('Personel', backref=db.backref('demirbas_listesi', lazy='dynamic'))
    hareketler = db.relationship('DemirbasHareket', backref='demirbas', lazy='dynamic',
                                  cascade='all, delete-orphan')

    KATEGORILER = [
        ('mobilya', 'Mobilya'), ('elektronik', 'Elektronik'),
        ('egitim_malzemesi', 'Egitim Malzemesi'), ('spor', 'Spor Malzemesi'),
        ('diger', 'Diger'),
    ]

    DURUMLAR = [
        ('aktif', 'Aktif'), ('arizali', 'Arizali'),
        ('hurda', 'Hurda'), ('kayip', 'Kayip'),
    ]

    @property
    def durum_badge(self):
        return {'aktif': 'success', 'arizali': 'warning', 'hurda': 'danger', 'kayip': 'dark'}.get(self.durum, 'secondary')

    @property
    def durum_str(self):
        return dict(self.DURUMLAR).get(self.durum, self.durum)

    def __repr__(self):
        return f'<Demirbas {self.ad}>'


class DemirbasHareket(db.Model):
    __tablename__ = 'demirbas_hareketler'

    id = db.Column(db.Integer, primary_key=True)
    demirbas_id = db.Column(db.Integer, db.ForeignKey('demirbaslar.id'), nullable=False)
    hareket_tipi = db.Column(db.String(20), nullable=False)
    eski_konum = db.Column(db.String(200), nullable=True)
    yeni_konum = db.Column(db.String(200), nullable=True)
    eski_sorumlu_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=True)
    yeni_sorumlu_id = db.Column(db.Integer, db.ForeignKey('personeller.id'), nullable=True)
    tarih = db.Column(db.Date, nullable=False, default=date.today)
    aciklama = db.Column(db.Text, nullable=True)

    eski_sorumlu = db.relationship('Personel', foreign_keys=[eski_sorumlu_id])
    yeni_sorumlu = db.relationship('Personel', foreign_keys=[yeni_sorumlu_id])

    HAREKET_TIPLERI = [
        ('zimmet', 'Zimmet'), ('iade', 'Iade'), ('transfer', 'Transfer'),
        ('ariza', 'Ariza'), ('hurda', 'Hurda'),
    ]

    @property
    def hareket_tipi_str(self):
        return dict(self.HAREKET_TIPLERI).get(self.hareket_tipi, self.hareket_tipi)

    def __repr__(self):
        return f'<DemirbasHareket {self.hareket_tipi}>'
