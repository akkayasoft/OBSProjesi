from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField, SubmitField,
                     FloatField, DateField)
from wtforms.validators import DataRequired, Optional, Length


class DemirbasForm(FlaskForm):
    ad = StringField('Demirbas Adi', validators=[DataRequired(), Length(max=300)])
    barkod = StringField('Barkod', validators=[Optional(), Length(max=50)])
    kategori = SelectField('Kategori', choices=[
        ('mobilya', 'Mobilya'), ('elektronik', 'Elektronik'),
        ('egitim_malzemesi', 'Egitim Malzemesi'), ('spor', 'Spor Malzemesi'),
        ('diger', 'Diger'),
    ], validators=[DataRequired()])
    marka = StringField('Marka', validators=[Optional(), Length(max=100)])
    model_adi = StringField('Model', validators=[Optional(), Length(max=100)])
    seri_no = StringField('Seri No', validators=[Optional(), Length(max=100)])
    edinme_tarihi = DateField('Edinme Tarihi', validators=[Optional()])
    edinme_fiyati = FloatField('Edinme Fiyati (TL)', validators=[Optional()])
    konum = StringField('Konum', validators=[DataRequired(), Length(max=200)])
    sorumlu_id = SelectField('Sorumlu', coerce=int, validators=[Optional()])
    durum = SelectField('Durum', choices=[
        ('aktif', 'Aktif'), ('arizali', 'Arizali'),
        ('hurda', 'Hurda'), ('kayip', 'Kayip'),
    ], validators=[DataRequired()])
    aciklama = TextAreaField('Aciklama', validators=[Optional()], render_kw={'rows': 2})
    submit = SubmitField('Kaydet')


class HareketForm(FlaskForm):
    hareket_tipi = SelectField('Hareket Tipi', choices=[
        ('zimmet', 'Zimmet'), ('iade', 'Iade'), ('transfer', 'Transfer'),
        ('ariza', 'Ariza'), ('hurda', 'Hurda'),
    ], validators=[DataRequired()])
    yeni_konum = StringField('Yeni Konum', validators=[Optional(), Length(max=200)])
    yeni_sorumlu_id = SelectField('Yeni Sorumlu', coerce=int, validators=[Optional()])
    tarih = DateField('Tarih', validators=[DataRequired()])
    aciklama = TextAreaField('Aciklama', validators=[Optional()], render_kw={'rows': 2})
    submit = SubmitField('Kaydet')
