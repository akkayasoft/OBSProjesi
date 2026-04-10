from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField, SubmitField,
                     IntegerField, DateField, BooleanField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class YurtOdaForm(FlaskForm):
    oda_no = StringField('Oda No', validators=[DataRequired(), Length(max=20)])
    bina = StringField('Bina', validators=[Optional(), Length(max=100)])
    kat = IntegerField('Kat', validators=[DataRequired(), NumberRange(min=-2, max=20)])
    kapasite = IntegerField('Kapasite', validators=[DataRequired(), NumberRange(min=1, max=20)])
    cinsiyet = SelectField('Cinsiyet', choices=[
        ('erkek', 'Erkek'), ('kiz', 'Kiz'), ('karma', 'Karma'),
    ], validators=[DataRequired()])
    durum = SelectField('Durum', choices=[
        ('aktif', 'Aktif'), ('bakim', 'Bakim'), ('kapali', 'Kapali'),
    ], validators=[DataRequired()])
    aciklama = TextAreaField('Aciklama', validators=[Optional()], render_kw={'rows': 2})
    submit = SubmitField('Kaydet')


class YurtKayitForm(FlaskForm):
    oda_id = SelectField('Oda', coerce=int, validators=[DataRequired()])
    ogrenci_id = SelectField('Ogrenci', coerce=int, validators=[DataRequired()])
    yatak_no = StringField('Yatak No', validators=[Optional(), Length(max=10)])
    baslangic_tarihi = DateField('Baslangic Tarihi', validators=[DataRequired()])
    submit = SubmitField('Kaydet')
