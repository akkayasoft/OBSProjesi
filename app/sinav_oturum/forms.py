from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, DateField, TimeField)
from wtforms.validators import DataRequired, Optional, Length


class SinavOturumForm(FlaskForm):
    """Sinav oturumu formu"""
    ad = StringField('Sinav Adi', validators=[
        DataRequired(message='Sinav adi zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Sinav adini giriniz'})
    sinav_turu = SelectField('Sinav Turu', choices=[
        ('yazili', 'Yazili'),
        ('sozlu', 'Sozlu'),
        ('test', 'Test'),
        ('performans', 'Performans'),
    ], validators=[DataRequired()])
    tarih = DateField('Tarih', validators=[DataRequired(message='Tarih alani zorunludur.')])
    baslangic_saati = TimeField('Baslangic Saati', validators=[
        DataRequired(message='Baslangic saati zorunludur.')
    ])
    bitis_saati = TimeField('Bitis Saati', validators=[
        DataRequired(message='Bitis saati zorunludur.')
    ])
    sinif_id = SelectField('Sinif', coerce=int,
                           validators=[DataRequired(message='Sinif secimi zorunludur.')])
    ders_id = SelectField('Ders', coerce=int,
                          validators=[DataRequired(message='Ders secimi zorunludur.')])
    ogretmen_id = SelectField('Ogretmen', coerce=int,
                              validators=[DataRequired(message='Ogretmen secimi zorunludur.')])
    derslik = StringField('Derslik', validators=[
        Optional(), Length(max=100)
    ], render_kw={'placeholder': 'Derslik / Salon bilgisi'})
    durum = SelectField('Durum', choices=[
        ('planlanmis', 'Planlanmis'),
        ('devam_ediyor', 'Devam Ediyor'),
        ('tamamlandi', 'Tamamlandi'),
        ('iptal', 'Iptal'),
    ], validators=[DataRequired()])
    aciklama = TextAreaField('Aciklama', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Sinav ile ilgili aciklama giriniz', 'rows': 3})
    submit = SubmitField('Kaydet')


class GozetmenForm(FlaskForm):
    """Gozetmen atama formu"""
    ogretmen_id = SelectField('Ogretmen', coerce=int,
                              validators=[DataRequired(message='Ogretmen secimi zorunludur.')])
    gorev = SelectField('Gorev', choices=[
        ('gozetmen', 'Gozetmen'),
        ('basgozetmen', 'Bas Gozetmen'),
    ], validators=[DataRequired()])
    submit = SubmitField('Gozetmen Ata')
