from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, FloatField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class KarneForm(FlaskForm):
    """Karne olusturma / duzenleme formu"""
    ogrenci_id = SelectField('Ogrenci', coerce=int,
                             validators=[DataRequired(message='Ogrenci secimi zorunludur.')])
    donem = SelectField('Donem', choices=[
        ('1. Donem', '1. Donem'),
        ('2. Donem', '2. Donem'),
    ], validators=[DataRequired(message='Donem secimi zorunludur.')])
    ogretim_yili = StringField('Ogretim Yili', validators=[
        DataRequired(message='Ogretim yili zorunludur.'),
        Length(min=9, max=20)
    ], render_kw={'placeholder': '2025-2026'})
    sinif_id = SelectField('Sinif', coerce=int,
                           validators=[DataRequired(message='Sinif secimi zorunludur.')])
    davranis_notu = SelectField('Davranis Notu', choices=[
        ('', 'Seciniz'),
        ('Cok Iyi', 'Cok Iyi'),
        ('Iyi', 'Iyi'),
        ('Orta', 'Orta'),
        ('Yetersiz', 'Yetersiz'),
    ], validators=[Optional()])
    devamsizlik_ozetsiz = FloatField('Ozursuz Devamsizlik (Gun)', validators=[
        Optional(), NumberRange(min=0)
    ], default=0)
    devamsizlik_ozetli = FloatField('Ozurlu Devamsizlik (Gun)', validators=[
        Optional(), NumberRange(min=0)
    ], default=0)
    sinif_ogretmeni_notu = TextAreaField('Sinif Ogretmeni Notu', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Sinif ogretmeni degerlendirmesi', 'rows': 3})
    mudur_notu = TextAreaField('Mudur Notu', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Okul muduru notu', 'rows': 3})
    durum = SelectField('Durum', choices=[
        ('taslak', 'Taslak'),
        ('onaylandi', 'Onaylandi'),
        ('basildi', 'Basildi'),
    ], validators=[DataRequired()])
    submit = SubmitField('Kaydet')


class KarneDersNotuForm(FlaskForm):
    """Karne ders notu formu"""
    ders_adi = StringField('Ders Adi', validators=[
        DataRequired(message='Ders adi zorunludur.'),
        Length(min=2, max=200)
    ])
    ders_kodu = StringField('Ders Kodu', validators=[
        Optional(), Length(max=50)
    ])
    sinav1 = FloatField('1. Sinav', validators=[
        Optional(), NumberRange(min=0, max=100)
    ])
    sinav2 = FloatField('2. Sinav', validators=[
        Optional(), NumberRange(min=0, max=100)
    ])
    sinav3 = FloatField('3. Sinav', validators=[
        Optional(), NumberRange(min=0, max=100)
    ])
    ortalama = FloatField('Ortalama', validators=[
        Optional(), NumberRange(min=0, max=100)
    ])
    performans = FloatField('Performans', validators=[
        Optional(), NumberRange(min=0, max=100)
    ])
    proje = FloatField('Proje', validators=[
        Optional(), NumberRange(min=0, max=100)
    ])
    yilsonu = FloatField('Yilsonu Notu', validators=[
        Optional(), NumberRange(min=0, max=100)
    ])
    harf_notu = StringField('Harf Notu', validators=[
        Optional(), Length(max=5)
    ])
    submit = SubmitField('Kaydet')


class TopluKarneForm(FlaskForm):
    """Sinif bazinda toplu karne olusturma formu"""
    sinif_id = SelectField('Sinif', coerce=int,
                           validators=[DataRequired(message='Sinif secimi zorunludur.')])
    donem = SelectField('Donem', choices=[
        ('1. Donem', '1. Donem'),
        ('2. Donem', '2. Donem'),
    ], validators=[DataRequired(message='Donem secimi zorunludur.')])
    ogretim_yili = StringField('Ogretim Yili', validators=[
        DataRequired(message='Ogretim yili zorunludur.'),
        Length(min=9, max=20)
    ], render_kw={'placeholder': '2025-2026'})
    submit = SubmitField('Karneleri Olustur')
