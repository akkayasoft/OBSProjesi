from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, IntegerField,
                     TextAreaField, SubmitField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


# === Ders Formu ===

class DersForm(FlaskForm):
    kod = StringField('Ders Kodu', validators=[
        DataRequired(), Length(min=2, max=20)
    ], render_kw={'placeholder': 'Örn: MAT101'})
    ad = StringField('Ders Adı', validators=[
        DataRequired(), Length(min=2, max=100)
    ], render_kw={'placeholder': 'Örn: Matematik'})
    kategori = SelectField('Kategori', choices=[
        ('Matematik', 'Matematik'),
        ('Fen', 'Fen Bilimleri'),
        ('Sosyal', 'Sosyal Bilimler'),
        ('Dil', 'Dil'),
        ('Sanat', 'Sanat'),
        ('Spor', 'Spor'),
        ('Bilisim', 'Bilişim'),
        ('Diger', 'Diğer'),
    ], validators=[DataRequired()])
    haftalik_saat = IntegerField('Haftalık Saat', validators=[
        DataRequired(), NumberRange(min=1, max=20)
    ], default=4)
    sinif_seviyesi = SelectField('Sınıf Seviyesi', choices=[
        (9, '9. Sınıf'), (10, '10. Sınıf'),
        (11, '11. Sınıf'), (12, '12. Sınıf'),
    ], coerce=int, validators=[DataRequired()])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Kaydet')


# === Ders Programı Formu ===

class DersProgramiForm(FlaskForm):
    ders_id = SelectField('Ders', coerce=int, validators=[DataRequired()])
    ogretmen_id = SelectField('Öğretmen', coerce=int, validators=[DataRequired()])
    sube_id = SelectField('Sınıf / Şube', coerce=int, validators=[DataRequired()])
    gun = SelectField('Gün', choices=[
        ('Pazartesi', 'Pazartesi'),
        ('Salı', 'Salı'),
        ('Çarşamba', 'Çarşamba'),
        ('Perşembe', 'Perşembe'),
        ('Cuma', 'Cuma'),
    ], validators=[DataRequired()])
    ders_saati = SelectField('Ders Saati', choices=[
        (1, '1. Ders'), (2, '2. Ders'), (3, '3. Ders'), (4, '4. Ders'),
        (5, '5. Ders'), (6, '6. Ders'), (7, '7. Ders'), (8, '8. Ders'),
    ], coerce=int, validators=[DataRequired()])
    donem = StringField('Dönem', validators=[
        DataRequired(), Length(max=20)
    ], render_kw={'placeholder': '2025-2026'})
    derslik = StringField('Derslik', validators=[
        Optional(), Length(max=50)
    ], render_kw={'placeholder': 'Örn: A-101'})
    submit = SubmitField('Kaydet')


# === Öğretmen Ders Atama Formu ===

class OgretmenDersAtamaForm(FlaskForm):
    ogretmen_id = SelectField('Öğretmen', coerce=int, validators=[DataRequired()])
    ders_id = SelectField('Ders', coerce=int, validators=[DataRequired()])
    sube_id = SelectField('Sınıf / Şube', coerce=int, validators=[DataRequired()])
    donem = StringField('Dönem', validators=[
        DataRequired(), Length(max=20)
    ], render_kw={'placeholder': '2025-2026'})
    submit = SubmitField('Kaydet')
