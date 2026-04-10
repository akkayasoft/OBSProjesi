from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, DateField)
from wtforms.validators import DataRequired, Optional, Length


class OdevForm(FlaskForm):
    """Odev olusturma/duzenleme formu"""
    baslik = StringField('Odev Basligi', validators=[
        DataRequired(), Length(min=2, max=200)
    ], render_kw={'placeholder': 'Orn: Konu Tekrar Odevi'})
    ders_id = SelectField('Ders', coerce=int, validators=[DataRequired()])
    sube_id = SelectField('Sinif / Sube', coerce=int, validators=[DataRequired()])
    ogretmen_id = SelectField('Ogretmen', coerce=int, validators=[DataRequired()])
    son_teslim_tarihi = DateField('Son Teslim Tarihi', validators=[DataRequired()], format='%Y-%m-%d')
    donem = StringField('Donem', validators=[
        DataRequired(), Length(max=20)
    ], render_kw={'placeholder': '2025-2026'})
    aciklama = TextAreaField('Aciklama', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Kaydet')


class OdevTeslimForm(FlaskForm):
    """Odev teslim takip formu"""
    submit = SubmitField('Teslim Durumlarini Kaydet')
