from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, BooleanField, IntegerField,
                     FloatField, DateField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class GuzergahForm(FlaskForm):
    """Guzergah olusturma/duzenleme formu"""
    ad = StringField('Guzergah Adi', validators=[
        DataRequired(message='Guzergah adi zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Ornek: Guzergah 1'})
    kod = StringField('Guzergah Kodu', validators=[
        DataRequired(message='Guzergah kodu zorunludur.'),
        Length(min=2, max=20)
    ], render_kw={'placeholder': 'Ornek: G01'})
    aciklama = TextAreaField('Aciklama', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Guzergah aciklamasi', 'rows': 3})
    baslangic_noktasi = StringField('Baslangic Noktasi', validators=[
        DataRequired(message='Baslangic noktasi zorunludur.'),
        Length(max=200)
    ], render_kw={'placeholder': 'Ornek: Kadikoy'})
    bitis_noktasi = StringField('Bitis Noktasi', validators=[
        DataRequired(message='Bitis noktasi zorunludur.'),
        Length(max=200)
    ], render_kw={'placeholder': 'Ornek: Okul'})
    mesafe_km = FloatField('Mesafe (km)', validators=[
        Optional()
    ], render_kw={'placeholder': 'Ornek: 15.5'})
    tahmini_sure = IntegerField('Tahmini Sure (dk)', validators=[
        Optional(), NumberRange(min=1, max=300)
    ], render_kw={'placeholder': 'Ornek: 45'})
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')


class DurakForm(FlaskForm):
    """Durak olusturma/duzenleme formu"""
    ad = StringField('Durak Adi', validators=[
        DataRequired(message='Durak adi zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Ornek: Kadikoy Meydani'})
    sira = IntegerField('Sira No', validators=[
        DataRequired(message='Sira numarasi zorunludur.'),
        NumberRange(min=1, max=100)
    ], render_kw={'placeholder': 'Ornek: 1'})
    tahmini_varis = StringField('Tahmini Varis Saati', validators=[
        Optional(), Length(max=10)
    ], render_kw={'placeholder': 'Ornek: 07:30'})
    adres = TextAreaField('Adres', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Durak adresi', 'rows': 2})
    submit = SubmitField('Kaydet')


class AracForm(FlaskForm):
    """Arac olusturma/duzenleme formu"""
    plaka = StringField('Plaka', validators=[
        DataRequired(message='Plaka zorunludur.'),
        Length(min=5, max=20)
    ], render_kw={'placeholder': 'Ornek: 34 ABC 123'})
    marka = StringField('Marka', validators=[
        DataRequired(message='Marka zorunludur.'),
        Length(max=100)
    ], render_kw={'placeholder': 'Ornek: Mercedes'})
    model = StringField('Model', validators=[
        DataRequired(message='Model zorunludur.'),
        Length(max=100)
    ], render_kw={'placeholder': 'Ornek: Sprinter'})
    kapasite = IntegerField('Kapasite', validators=[
        DataRequired(message='Kapasite zorunludur.'),
        NumberRange(min=1, max=100)
    ], render_kw={'placeholder': 'Ornek: 30'})
    sofor_adi = StringField('Sofor Adi', validators=[
        DataRequired(message='Sofor adi zorunludur.'),
        Length(max=200)
    ], render_kw={'placeholder': 'Ornek: Ahmet Yilmaz'})
    sofor_telefon = StringField('Sofor Telefon', validators=[
        Optional(), Length(max=20)
    ], render_kw={'placeholder': 'Ornek: 05301234567'})
    guzergah_id = SelectField('Guzergah', coerce=int, validators=[Optional()])
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')


class ServisKayitForm(FlaskForm):
    """Servis kayit formu"""
    ogrenci_id = SelectField('Ogrenci', coerce=int,
                             validators=[DataRequired(message='Ogrenci secimi zorunludur.')])
    guzergah_id = SelectField('Guzergah', coerce=int,
                              validators=[DataRequired(message='Guzergah secimi zorunludur.')])
    durak_id = SelectField('Durak', coerce=int, validators=[Optional()])
    binis_yonu = SelectField('Binis Yonu', choices=[
        ('her_ikisi', 'Gidis-Donus'),
        ('gidis', 'Gidis'),
        ('donus', 'Donus'),
    ], validators=[DataRequired()])
    baslangic_tarihi = DateField('Baslangic Tarihi', validators=[
        DataRequired(message='Baslangic tarihi zorunludur.')
    ])
    bitis_tarihi = DateField('Bitis Tarihi', validators=[Optional()])
    ucret = FloatField('Aylik Ucret (TL)', validators=[
        Optional()
    ], render_kw={'placeholder': 'Ornek: 2500'})
    durum = SelectField('Durum', choices=[
        ('aktif', 'Aktif'),
        ('pasif', 'Pasif'),
        ('iptal', 'Iptal'),
    ], validators=[DataRequired()])
    submit = SubmitField('Kaydet')
