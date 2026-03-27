from flask_wtf import FlaskForm
from wtforms import (SelectField, DateField, TextAreaField, SubmitField,
                     SelectMultipleField, widgets)
from wtforms.validators import DataRequired, Optional
from datetime import date


class YoklamaSecimForm(FlaskForm):
    """Yoklama alınacak sınıf ve tarih seçimi"""
    sube_id = SelectField('Sınıf / Şube', coerce=int, validators=[DataRequired()])
    tarih = DateField('Tarih', default=date.today, validators=[DataRequired()])
    ders_saati = SelectField('Ders Saati', coerce=int, choices=[
        (1, '1. Ders'), (2, '2. Ders'), (3, '3. Ders'), (4, '4. Ders'),
        (5, '5. Ders'), (6, '6. Ders'), (7, '7. Ders'), (8, '8. Ders'),
    ], validators=[DataRequired()])
    submit = SubmitField('Yoklama Al')


class TopluYoklamaSecimForm(FlaskForm):
    """Tüm gün yoklama alınacak sınıf ve tarih seçimi"""
    sube_id = SelectField('Sınıf / Şube', coerce=int, validators=[DataRequired()])
    tarih = DateField('Tarih', default=date.today, validators=[DataRequired()])
    ders_saatleri = SelectMultipleField('Ders Saatleri', coerce=int, choices=[
        (1, '1. Ders'), (2, '2. Ders'), (3, '3. Ders'), (4, '4. Ders'),
        (5, '5. Ders'), (6, '6. Ders'), (7, '7. Ders'), (8, '8. Ders'),
    ], option_widget=widgets.CheckboxInput(),
       widget=widgets.ListWidget(prefix_label=False),
       validators=[DataRequired(message='En az bir ders saati seçiniz.')])
    submit = SubmitField('Yoklama Al')


class DevamsizlikRaporForm(FlaskForm):
    """Devamsızlık rapor filtresi"""
    sube_id = SelectField('Sınıf / Şube', coerce=int, validators=[Optional()])
    baslangic = DateField('Başlangıç', validators=[Optional()])
    bitis = DateField('Bitiş', validators=[Optional()])
    submit = SubmitField('Filtrele')
