from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, DateField)
from wtforms.validators import DataRequired, Optional, Length


class SinavForm(FlaskForm):
    """Sınav oluşturma/düzenleme formu"""
    ad = StringField('Sınav Adı', validators=[
        DataRequired(), Length(min=2, max=200)
    ], render_kw={'placeholder': 'Örn: 1. Dönem 1. Yazılı'})
    sinav_turu_id = SelectField('Sınav Türü', coerce=int, validators=[DataRequired()])
    ders_id = SelectField('Ders', coerce=int, validators=[DataRequired()])
    sube_id = SelectField('Sınıf / Şube', coerce=int, validators=[DataRequired()])
    ogretmen_id = SelectField('Öğretmen', coerce=int, validators=[DataRequired()])
    tarih = DateField('Sınav Tarihi', validators=[DataRequired()], format='%Y-%m-%d')
    donem = StringField('Dönem', validators=[
        DataRequired(), Length(max=20)
    ], render_kw={'placeholder': '2025-2026'})
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Kaydet')


class NotGirisForm(FlaskForm):
    """Not giriş formu (tekil, toplu giriş için template'de kullanılır)"""
    submit = SubmitField('Notları Kaydet')


