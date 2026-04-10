from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    ad = db.Column(db.String(100), nullable=False)
    soyad = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='muhasebeci')
    aktif = db.Column(db.Boolean, default=True)
    olusturma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def tam_ad(self):
        return f"{self.ad} {self.soyad}"

    @property
    def is_admin(self):
        return self.rol == 'admin'

    @property
    def is_ogretmen(self):
        return self.rol == 'ogretmen'

    @property
    def is_veli(self):
        return self.rol == 'veli'

    @property
    def is_ogrenci(self):
        return self.rol == 'ogrenci'

    @property
    def is_muhasebeci(self):
        return self.rol == 'muhasebeci'

    @property
    def rol_str(self):
        rol_map = {
            'admin': 'Yönetici',
            'ogretmen': 'Öğretmen',
            'veli': 'Veli',
            'ogrenci': 'Öğrenci',
            'muhasebeci': 'Muhasebeci',
        }
        return rol_map.get(self.rol, self.rol)

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
