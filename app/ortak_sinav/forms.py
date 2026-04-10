from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, IntegerField, DateField, FloatField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class OrtakSinavForm(FlaskForm):
    """Ortak sinav formu"""
    ad = StringField('Sinav Adi', validators=[
        DataRequired(message='Sinav adi zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Sinav adini giriniz'})
    ders_id = SelectField('Ders', coerce=int,
                          validators=[DataRequired(message='Ders secimi zorunludur.')])
    seviye = SelectField('Sinif Seviyesi', coerce=int, choices=[
        (9, '9. Sinif'),
        (10, '10. Sinif'),
        (11, '11. Sinif'),
        (12, '12. Sinif'),
    ], validators=[DataRequired()])
    donem = StringField('Donem', validators=[
        DataRequired(message='Donem alani zorunludur.'),
        Length(max=20)
    ], render_kw={'placeholder': 'Orn: 2025-2026'})
    tarih = DateField('Sinav Tarihi', validators=[DataRequired(message='Tarih alani zorunludur.')])
    sure_dakika = IntegerField('Sure (Dakika)', validators=[
        DataRequired(message='Sure alani zorunludur.'),
        NumberRange(min=5, max=300, message='Sure 5-300 dakika arasinda olmalidir.')
    ], default=40)
    soru_sayisi = IntegerField('Soru Sayisi', validators=[
        DataRequired(message='Soru sayisi zorunludur.'),
        NumberRange(min=1, max=200, message='Soru sayisi 1-200 arasinda olmalidir.')
    ], default=20)
    toplam_puan = FloatField('Toplam Puan', validators=[
        DataRequired(message='Toplam puan zorunludur.'),
        NumberRange(min=1, max=1000, message='Toplam puan 1-1000 arasinda olmalidir.')
    ], default=100)
    durum = SelectField('Durum', choices=[
        ('hazirlaniyor', 'Hazirlaniyor'),
        ('uygulanmis', 'Uygulanmis'),
        ('degerlendirme', 'Degerlendirme'),
        ('tamamlandi', 'Tamamlandi'),
    ], validators=[DataRequired()])
    aciklama = TextAreaField('Aciklama', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Sinav aciklamasi (istege bagli)', 'rows': 3})
    submit = SubmitField('Kaydet')


class SonucGirisiForm(FlaskForm):
    """Tekil sonuc girisi formu"""
    ogrenci_id = SelectField('Ogrenci', coerce=int,
                             validators=[DataRequired(message='Ogrenci secimi zorunludur.')])
    sube_id = SelectField('Sube', coerce=int,
                          validators=[DataRequired(message='Sube secimi zorunludur.')])
    puan = FloatField('Puan', validators=[
        DataRequired(message='Puan alani zorunludur.'),
        NumberRange(min=0, max=1000, message='Puan 0 ile toplam puan arasinda olmalidir.')
    ], default=0)
    dogru_sayisi = IntegerField('Dogru Sayisi', validators=[Optional()])
    yanlis_sayisi = IntegerField('Yanlis Sayisi', validators=[Optional()])
    bos_sayisi = IntegerField('Bos Sayisi', validators=[Optional()])
    submit = SubmitField('Kaydet')
