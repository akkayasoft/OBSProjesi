from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField, SubmitField,
                     IntegerField, FloatField, DateField, BooleanField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class YemekMenuForm(FlaskForm):
    tarih = DateField('Tarih', validators=[DataRequired()])
    gun = SelectField('Gun', choices=[
        ('Pazartesi', 'Pazartesi'), ('Sali', 'Sali'), ('Carsamba', 'Carsamba'),
        ('Persembe', 'Persembe'), ('Cuma', 'Cuma'),
    ], validators=[DataRequired()])
    kahvalti = TextAreaField('Kahvalti', validators=[Optional()], render_kw={'rows': 2})
    ogle_yemegi = TextAreaField('Ogle Yemegi', validators=[DataRequired()], render_kw={'rows': 2})
    ara_ogun = TextAreaField('Ara Ogun', validators=[Optional()], render_kw={'rows': 2})
    kalori = IntegerField('Kalori (kcal)', validators=[Optional()])
    aciklama = TextAreaField('Aciklama', validators=[Optional()], render_kw={'rows': 2})
    submit = SubmitField('Kaydet')


class KantinUrunForm(FlaskForm):
    ad = StringField('Urun Adi', validators=[DataRequired(), Length(max=200)])
    kategori = SelectField('Kategori', choices=[
        ('yiyecek', 'Yiyecek'), ('icecek', 'Icecek'), ('atistirmalik', 'Atistirmalik'),
    ], validators=[DataRequired()])
    fiyat = FloatField('Fiyat (TL)', validators=[DataRequired()])
    stok = IntegerField('Stok', validators=[DataRequired(), NumberRange(min=0)])
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')


class KantinSatisForm(FlaskForm):
    urun_id = SelectField('Urun', coerce=int, validators=[DataRequired()])
    ogrenci_id = SelectField('Ogrenci', coerce=int, validators=[Optional()])
    miktar = IntegerField('Miktar', validators=[DataRequired(), NumberRange(min=1)], default=1)
    submit = SubmitField('Satis Yap')
