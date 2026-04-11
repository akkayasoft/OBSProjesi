from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, PasswordField,
                     SubmitField, BooleanField)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, ValidationError
from app.models.user import User


class KullaniciForm(FlaskForm):
    """Yeni kullanici olusturma formu"""
    username = StringField('Kullanici Adi', validators=[
        DataRequired(message='Kullanici adi zorunludur.'),
        Length(min=3, max=80, message='Kullanici adi 3-80 karakter olmalidir.')
    ], render_kw={'placeholder': 'Kullanici adini giriniz'})
    email = StringField('E-posta', validators=[
        DataRequired(message='E-posta zorunludur.'),
        Email(message='Gecerli bir e-posta adresi giriniz.'),
        Length(max=120)
    ], render_kw={'placeholder': 'E-posta adresini giriniz'})
    ad = StringField('Ad', validators=[
        DataRequired(message='Ad zorunludur.'),
        Length(min=2, max=100)
    ], render_kw={'placeholder': 'Adi giriniz'})
    soyad = StringField('Soyad', validators=[
        DataRequired(message='Soyad zorunludur.'),
        Length(min=2, max=100)
    ], render_kw={'placeholder': 'Soyadi giriniz'})
    rol = SelectField('Rol', choices=[
        ('admin', 'Sistem Yoneticisi'),
        ('yonetici', 'Dershane Yoneticisi'),
        ('ogretmen', 'Ogretmen'),
        ('veli', 'Veli'),
        ('ogrenci', 'Ogrenci'),
        ('muhasebeci', 'Muhasebeci'),
    ], validators=[DataRequired(message='Rol secimi zorunludur.')])
    password = PasswordField('Sifre', validators=[
        DataRequired(message='Sifre zorunludur.'),
        Length(min=6, message='Sifre en az 6 karakter olmalidir.')
    ], render_kw={'placeholder': 'Sifre giriniz'})
    password_confirm = PasswordField('Sifre Tekrar', validators=[
        DataRequired(message='Sifre tekrari zorunludur.'),
        EqualTo('password', message='Sifreler eslesmeli.')
    ], render_kw={'placeholder': 'Sifreyi tekrar giriniz'})
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError('Bu kullanici adi zaten kullanilmaktadir.')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user:
            raise ValidationError('Bu e-posta adresi zaten kullanilmaktadir.')


class KullaniciDuzenleForm(FlaskForm):
    """Kullanici duzenleme formu"""
    username = StringField('Kullanici Adi', validators=[
        DataRequired(message='Kullanici adi zorunludur.'),
        Length(min=3, max=80, message='Kullanici adi 3-80 karakter olmalidir.')
    ], render_kw={'placeholder': 'Kullanici adini giriniz'})
    email = StringField('E-posta', validators=[
        DataRequired(message='E-posta zorunludur.'),
        Email(message='Gecerli bir e-posta adresi giriniz.'),
        Length(max=120)
    ], render_kw={'placeholder': 'E-posta adresini giriniz'})
    ad = StringField('Ad', validators=[
        DataRequired(message='Ad zorunludur.'),
        Length(min=2, max=100)
    ], render_kw={'placeholder': 'Adi giriniz'})
    soyad = StringField('Soyad', validators=[
        DataRequired(message='Soyad zorunludur.'),
        Length(min=2, max=100)
    ], render_kw={'placeholder': 'Soyadi giriniz'})
    rol = SelectField('Rol', choices=[
        ('admin', 'Sistem Yoneticisi'),
        ('yonetici', 'Dershane Yoneticisi'),
        ('ogretmen', 'Ogretmen'),
        ('veli', 'Veli'),
        ('ogrenci', 'Ogrenci'),
        ('muhasebeci', 'Muhasebeci'),
    ], validators=[DataRequired(message='Rol secimi zorunludur.')])
    password = PasswordField('Yeni Sifre (bos birakilirsa degismez)', validators=[
        Optional(),
        Length(min=6, message='Sifre en az 6 karakter olmalidir.')
    ], render_kw={'placeholder': 'Yeni sifre (opsiyonel)'})
    password_confirm = PasswordField('Sifre Tekrar', validators=[
        EqualTo('password', message='Sifreler eslesmeli.')
    ], render_kw={'placeholder': 'Sifreyi tekrar giriniz'})
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Guncelle')

    def __init__(self, kullanici_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kullanici_id = kullanici_id

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user and user.id != self.kullanici_id:
            raise ValidationError('Bu kullanici adi zaten kullanilmaktadir.')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user and user.id != self.kullanici_id:
            raise ValidationError('Bu e-posta adresi zaten kullanilmaktadir.')


class SifreDegistirForm(FlaskForm):
    """Kullanicinin kendi sifresini degistirme formu"""
    current_password = PasswordField('Mevcut Sifre', validators=[
        DataRequired(message='Mevcut sifre zorunludur.')
    ], render_kw={'placeholder': 'Mevcut sifrenizi giriniz'})
    new_password = PasswordField('Yeni Sifre', validators=[
        DataRequired(message='Yeni sifre zorunludur.'),
        Length(min=6, message='Sifre en az 6 karakter olmalidir.')
    ], render_kw={'placeholder': 'Yeni sifrenizi giriniz'})
    confirm_password = PasswordField('Yeni Sifre Tekrar', validators=[
        DataRequired(message='Sifre tekrari zorunludur.'),
        EqualTo('new_password', message='Sifreler eslesmeli.')
    ], render_kw={'placeholder': 'Yeni sifreyi tekrar giriniz'})
    submit = SubmitField('Sifreyi Degistir')


class YoneticiForm(FlaskForm):
    """Dershane Yoneticisi olusturma formu.

    Sade kullanici bilgileri + preset secici. Preset checkbox'lari
    sayfa yuklenirken javascript ile dolduracak; asil modul secimleri
    (moduller) sonraki ekranda ayri bir form olarak kaydedilir.
    """
    username = StringField('Kullanici Adi', validators=[
        DataRequired(message='Kullanici adi zorunludur.'),
        Length(min=3, max=80)
    ], render_kw={'placeholder': 'ornegin: dershane1_admin'})
    email = StringField('E-posta', validators=[
        DataRequired(message='E-posta zorunludur.'),
        Email(message='Gecerli bir e-posta adresi giriniz.'),
        Length(max=120)
    ], render_kw={'placeholder': 'yonetici@dershane.com'})
    ad = StringField('Ad', validators=[
        DataRequired(message='Ad zorunludur.'),
        Length(min=2, max=100)
    ])
    soyad = StringField('Soyad', validators=[
        DataRequired(message='Soyad zorunludur.'),
        Length(min=2, max=100)
    ])
    password = PasswordField('Sifre', validators=[
        DataRequired(message='Sifre zorunludur.'),
        Length(min=6, message='Sifre en az 6 karakter olmalidir.')
    ])
    password_confirm = PasswordField('Sifre Tekrar', validators=[
        DataRequired(message='Sifre tekrari zorunludur.'),
        EqualTo('password', message='Sifreler eslesmeli.')
    ])
    preset = SelectField('Modul Paketi', choices=[
        ('baslangic', 'Baslangic - Temel modul seti'),
        ('standart', 'Standart - Akademik ve operasyonel'),
        ('kurumsal', 'Kurumsal - Tum is modulleri'),
        ('ozel', 'Ozel - Asagidan sec'),
    ], default='standart')
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user:
            raise ValidationError('Bu kullanici adi zaten kullanilmaktadir.')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user:
            raise ValidationError('Bu e-posta adresi zaten kullanilmaktadir.')


class YoneticiDuzenleForm(FlaskForm):
    """Dershane Yoneticisi duzenleme formu (sifre opsiyonel)."""
    username = StringField('Kullanici Adi', validators=[
        DataRequired(message='Kullanici adi zorunludur.'),
        Length(min=3, max=80)
    ])
    email = StringField('E-posta', validators=[
        DataRequired(message='E-posta zorunludur.'),
        Email(),
        Length(max=120)
    ])
    ad = StringField('Ad', validators=[DataRequired(), Length(min=2, max=100)])
    soyad = StringField('Soyad', validators=[DataRequired(), Length(min=2, max=100)])
    password = PasswordField('Yeni Sifre (bos birakilirsa degismez)', validators=[
        Optional(),
        Length(min=6, message='Sifre en az 6 karakter olmalidir.')
    ])
    password_confirm = PasswordField('Sifre Tekrar', validators=[
        EqualTo('password', message='Sifreler eslesmeli.')
    ])
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Guncelle')

    def __init__(self, kullanici_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kullanici_id = kullanici_id

    def validate_username(self, field):
        user = User.query.filter_by(username=field.data).first()
        if user and user.id != self.kullanici_id:
            raise ValidationError('Bu kullanici adi zaten kullanilmaktadir.')

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user and user.id != self.kullanici_id:
            raise ValidationError('Bu e-posta adresi zaten kullanilmaktadir.')


class ProfilForm(FlaskForm):
    """Kullanicinin kendi profilini duzenleme formu"""
    ad = StringField('Ad', validators=[
        DataRequired(message='Ad zorunludur.'),
        Length(min=2, max=100)
    ], render_kw={'placeholder': 'Adinizi giriniz'})
    soyad = StringField('Soyad', validators=[
        DataRequired(message='Soyad zorunludur.'),
        Length(min=2, max=100)
    ], render_kw={'placeholder': 'Soyadinizi giriniz'})
    email = StringField('E-posta', validators=[
        DataRequired(message='E-posta zorunludur.'),
        Email(message='Gecerli bir e-posta adresi giriniz.'),
        Length(max=120)
    ], render_kw={'placeholder': 'E-posta adresinizi giriniz'})
    submit = SubmitField('Guncelle')

    def __init__(self, kullanici_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kullanici_id = kullanici_id

    def validate_email(self, field):
        user = User.query.filter_by(email=field.data).first()
        if user and user.id != self.kullanici_id:
            raise ValidationError('Bu e-posta adresi zaten kullanilmaktadir.')
