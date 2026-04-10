from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, IntegerField, DateField, TimeField,
                     BooleanField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class EtutForm(FlaskForm):
    """Etut olusturma/duzenleme formu"""
    ad = StringField('Etut Adi', validators=[
        DataRequired(message='Etut adi zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Etut adini giriniz'})
    ders_id = SelectField('Ders', coerce=int, validators=[Optional()])
    ogretmen_id = SelectField('Ogretmen', coerce=int,
                               validators=[DataRequired(message='Ogretmen secimi zorunludur.')])
    sube_id = SelectField('Sube', coerce=int, validators=[Optional()])
    gun = SelectField('Gun', choices=[
        ('Pazartesi', 'Pazartesi'),
        ('Sali', 'Sali'),
        ('Carsamba', 'Carsamba'),
        ('Persembe', 'Persembe'),
        ('Cuma', 'Cuma'),
    ], validators=[DataRequired(message='Gun secimi zorunludur.')])
    baslangic_saati = TimeField('Baslangic Saati',
                                 validators=[DataRequired(message='Baslangic saati zorunludur.')])
    bitis_saati = TimeField('Bitis Saati',
                             validators=[DataRequired(message='Bitis saati zorunludur.')])
    derslik = StringField('Derslik', validators=[
        Optional(), Length(max=50)
    ], render_kw={'placeholder': 'Orn: A-301'})
    kontenjan = IntegerField('Kontenjan', validators=[
        DataRequired(message='Kontenjan zorunludur.'),
        NumberRange(min=1, max=200, message='Kontenjan 1-200 arasinda olmalidir.')
    ], default=30)
    donem = StringField('Donem', validators=[
        DataRequired(message='Donem zorunludur.'),
        Length(max=20)
    ], render_kw={'placeholder': 'Orn: 2025-2026'})
    aktif = BooleanField('Aktif', default=True)
    aciklama = TextAreaField('Aciklama', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Etut hakkinda aciklama', 'rows': 3})
    submit = SubmitField('Kaydet')


class EtutKatilimForm(FlaskForm):
    """Etut katilim formu"""
    tarih = DateField('Tarih', validators=[DataRequired(message='Tarih zorunludur.')])
    submit = SubmitField('Katilimi Kaydet')
