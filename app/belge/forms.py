from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Optional, Length


class BelgeForm(FlaskForm):
    baslik = StringField('Belge Adi', validators=[DataRequired(), Length(max=300)])
    kategori = SelectField('Kategori', choices=[
        ('resmi', 'Resmi Yazi'), ('genelge', 'Genelge'), ('yonerge', 'Yonerge'),
        ('form', 'Form / Sablon'), ('rapor', 'Rapor'), ('diger', 'Diger'),
    ], validators=[DataRequired()])
    aciklama = TextAreaField('Aciklama', validators=[Optional()], render_kw={'rows': 3})
    erisim = SelectField('Erisim', choices=[
        ('herkes', 'Herkes'), ('admin', 'Sadece Admin'),
        ('ogretmen', 'Ogretmenler'), ('personel', 'Personel'),
    ], validators=[DataRequired()])
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')
