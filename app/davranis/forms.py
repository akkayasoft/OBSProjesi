from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, IntegerField, DateField, BooleanField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class DavranisKaydiForm(FlaskForm):
    """Davranis degerlendirme kaydi formu"""
    ogrenci_id = SelectField('Ogrenci', coerce=int,
                             validators=[DataRequired(message='Ogrenci secimi zorunludur.')])
    ogretmen_id = SelectField('Ogretmen', coerce=int,
                              validators=[DataRequired(message='Ogretmen secimi zorunludur.')])
    sinif_id = SelectField('Sinif', coerce=int,
                           validators=[Optional()])
    kural_id = SelectField('Davranis Kurali', coerce=int,
                           validators=[Optional()])
    tarih = DateField('Tarih', validators=[DataRequired(message='Tarih alani zorunludur.')])
    tur = SelectField('Tur', choices=[
        ('olumlu', 'Olumlu'),
        ('olumsuz', 'Olumsuz'),
    ], validators=[DataRequired()])
    kategori = SelectField('Kategori', choices=[
        ('akademik', 'Akademik'),
        ('sosyal', 'Sosyal'),
        ('disiplin', 'Disiplin'),
        ('saglik', 'Saglik'),
        ('diger', 'Diger'),
    ], validators=[DataRequired()])
    puan = IntegerField('Puan (-10 ile +10 arasi)', validators=[
        DataRequired(message='Puan alani zorunludur.'),
        NumberRange(min=-10, max=10, message='Puan -10 ile +10 arasinda olmalidir.')
    ], default=0)
    aciklama = TextAreaField('Aciklama', validators=[
        DataRequired(message='Aciklama alani zorunludur.'),
        Length(max=5000)
    ], render_kw={'placeholder': 'Davranis aciklamasi giriniz', 'rows': 4})
    submit = SubmitField('Kaydet')


class DavranisKuraliForm(FlaskForm):
    """Davranis kurali formu"""
    ad = StringField('Kural Adi', validators=[
        DataRequired(message='Kural adi zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Kural adini giriniz'})
    kategori = SelectField('Kategori', choices=[
        ('akademik', 'Akademik'),
        ('sosyal', 'Sosyal'),
        ('disiplin', 'Disiplin'),
        ('saglik', 'Saglik'),
        ('diger', 'Diger'),
    ], validators=[DataRequired()])
    tur = SelectField('Tur', choices=[
        ('olumlu', 'Olumlu'),
        ('olumsuz', 'Olumsuz'),
    ], validators=[DataRequired()])
    varsayilan_puan = IntegerField('Varsayilan Puan (-10 ile +10 arasi)', validators=[
        DataRequired(message='Varsayilan puan zorunludur.'),
        NumberRange(min=-10, max=10, message='Puan -10 ile +10 arasinda olmalidir.')
    ], default=0)
    aciklama = TextAreaField('Aciklama', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Kural aciklamasi giriniz', 'rows': 3})
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')
