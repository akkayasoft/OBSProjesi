from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField, SubmitField,
                     IntegerField, DateField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class KitapForm(FlaskForm):
    baslik = StringField('Kitap Adi', validators=[DataRequired(), Length(max=300)])
    yazar = StringField('Yazar', validators=[DataRequired(), Length(max=200)])
    isbn = StringField('ISBN', validators=[Optional(), Length(max=20)])
    yayinevi = StringField('Yayinevi', validators=[Optional(), Length(max=200)])
    yayin_yili = IntegerField('Yayin Yili', validators=[Optional()])
    kategori = SelectField('Kategori', choices=[
        ('roman', 'Roman'), ('hikaye', 'Hikaye'), ('siir', 'Siir'),
        ('bilim', 'Bilim'), ('tarih', 'Tarih'), ('ders_kitabi', 'Ders Kitabi'),
        ('ansiklopedi', 'Ansiklopedi'), ('diger', 'Diger'),
    ], validators=[DataRequired()])
    raf_no = StringField('Raf No', validators=[Optional(), Length(max=50)])
    adet = IntegerField('Adet', validators=[DataRequired(), NumberRange(min=1)], default=1)
    aciklama = TextAreaField('Aciklama', validators=[Optional()], render_kw={'rows': 2})
    submit = SubmitField('Kaydet')


class OduncForm(FlaskForm):
    kitap_id = SelectField('Kitap', coerce=int, validators=[DataRequired()])
    kisi_turu = SelectField('Kisi Turu', choices=[
        ('ogrenci', 'Ogrenci'), ('personel', 'Personel')
    ], validators=[DataRequired()])
    ogrenci_id = SelectField('Ogrenci', coerce=int, validators=[Optional()])
    personel_id = SelectField('Personel', coerce=int, validators=[Optional()])
    son_iade_tarihi = DateField('Son Iade Tarihi', validators=[DataRequired()])
    aciklama = TextAreaField('Aciklama', validators=[Optional()], render_kw={'rows': 2})
    submit = SubmitField('Odunc Ver')
