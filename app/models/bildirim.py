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
