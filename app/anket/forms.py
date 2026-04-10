from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, DateField, BooleanField, IntegerField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class AnketForm(FlaskForm):
    """Anket olusturma / duzenleme formu"""
    baslik = StringField('Anket Basligi', validators=[
        DataRequired(message='Baslik alani zorunludur.'),
        Length(min=3, max=300, message='Baslik 3-300 karakter arasinda olmalidir.')
    ], render_kw={'placeholder': 'Anket basligini giriniz'})
    aciklama = TextAreaField('Aciklama', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Anket aciklamasini giriniz', 'rows': 3})
    hedef_kitle = SelectField('Hedef Kitle', choices=[
        ('tumu', 'Tumu'),
        ('ogretmen', 'Ogretmen'),
        ('ogrenci', 'Ogrenci'),
        ('veli', 'Veli'),
    ], validators=[DataRequired()])
    baslangic_tarihi = DateField('Baslangic Tarihi', validators=[
        DataRequired(message='Baslangic tarihi zorunludur.')
    ])
    bitis_tarihi = DateField('Bitis Tarihi', validators=[
        DataRequired(message='Bitis tarihi zorunludur.')
    ])
    anonim = BooleanField('Anonim Anket', default=True)
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')


class AnketSoruForm(FlaskForm):
    """Anket sorusu formu"""
    soru_metni = TextAreaField('Soru Metni', validators=[
        DataRequired(message='Soru metni zorunludur.'),
        Length(max=2000)
    ], render_kw={'placeholder': 'Soruyu giriniz', 'rows': 3})
    soru_tipi = SelectField('Soru Tipi', choices=[
        ('coktan_secmeli', 'Coktan Secmeli'),
        ('acik_uclu', 'Acik Uclu'),
        ('derecelendirme', 'Derecelendirme (1-5)'),
        ('evet_hayir', 'Evet / Hayir'),
    ], validators=[DataRequired()])
    secenekler = TextAreaField('Secenekler (her satira bir secenek)', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Her satira bir secenek yaziniz', 'rows': 4})
    sira = IntegerField('Sira', validators=[
        Optional(), NumberRange(min=0, message='Sira 0 veya daha buyuk olmalidir.')
    ], default=0)
    zorunlu = BooleanField('Zorunlu Soru', default=True)
    submit = SubmitField('Kaydet')
