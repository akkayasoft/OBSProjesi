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
