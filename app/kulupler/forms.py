from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, BooleanField, IntegerField,
                     DateTimeLocalField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class KulupForm(FlaskForm):
    """Kulup olusturma/duzenleme formu"""
    ad = StringField('Kulup Adi', validators=[
        DataRequired(message='Kulup adi zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Kulup adini giriniz'})
    aciklama = TextAreaField('Aciklama', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Kulup aciklamasi', 'rows': 4})
    kategori = SelectField('Kategori', choices=[
        ('spor', 'Spor'),
        ('sanat', 'Sanat'),
        ('bilim', 'Bilim'),
        ('sosyal', 'Sosyal'),
        ('kultur', 'Kultur'),
        ('diger', 'Diger'),
    ], validators=[DataRequired()])
    danisman_id = SelectField('Danisman Ogretmen', coerce=int,
                              validators=[DataRequired(message='Danisman secimi zorunludur.')])
    kontenjan = IntegerField('Kontenjan', default=30, validators=[
        DataRequired(), NumberRange(min=1, max=100)
    ])
    toplanti_gunu = SelectField('Toplanti Gunu', choices=[
        ('', 'Seciniz'),
        ('Pazartesi', 'Pazartesi'),
        ('Sali', 'Sali'),
        ('Carsamba', 'Carsamba'),
        ('Persembe', 'Persembe'),
        ('Cuma', 'Cuma'),
    ], validators=[Optional()])
    toplanti_saati = StringField('Toplanti Saati', validators=[
        Optional(), Length(max=20)
    ], render_kw={'placeholder': 'Ornek: 15:00-16:30'})
    toplanti_yeri = StringField('Toplanti Yeri', validators=[
        Optional(), Length(max=200)
    ], render_kw={'placeholder': 'Toplanti yeri'})
    donem = StringField('Donem', default='2025-2026', validators=[
        DataRequired(), Length(max=20)
    ])
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')


class KulupUyelikForm(FlaskForm):
    """Kulup uyelik formu"""
    ogrenci_id = SelectField('Ogrenci', coerce=int,
                             validators=[DataRequired(message='Ogrenci secimi zorunludur.')])
    gorev = SelectField('Gorev', choices=[
        ('uye', 'Uye'),
        ('baskan', 'Baskan'),
        ('baskan_yardimcisi', 'Baskan Yardimcisi'),
        ('sekreter', 'Sekreter'),
    ], validators=[DataRequired()])
    submit = SubmitField('Kaydet')


class KulupEtkinlikForm(FlaskForm):
    """Kulup etkinlik formu"""
    baslik = StringField('Etkinlik Basligi', validators=[
        DataRequired(message='Baslik zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Etkinlik basligini giriniz'})
    aciklama = TextAreaField('Aciklama', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Etkinlik aciklamasi', 'rows': 4})
    tarih = DateTimeLocalField('Tarih', format='%Y-%m-%dT%H:%M',
                               validators=[DataRequired(message='Tarih zorunludur.')])
    konum = StringField('Konum', validators=[
        Optional(), Length(max=200)
    ], render_kw={'placeholder': 'Etkinlik konumu'})
    tur = SelectField('Tur', choices=[
        ('toplanti', 'Toplanti'),
        ('yarisma', 'Yarisma'),
        ('gosteri', 'Gosteri'),
        ('gezi', 'Gezi'),
        ('diger', 'Diger'),
    ], validators=[DataRequired()])
    durum = SelectField('Durum', choices=[
        ('planlandi', 'Planlandi'),
        ('tamamlandi', 'Tamamlandi'),
        ('iptal', 'Iptal Edildi'),
    ], validators=[DataRequired()])
    submit = SubmitField('Kaydet')
