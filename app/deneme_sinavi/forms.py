from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SelectField, IntegerField, FloatField, TextAreaField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional, Length

from app.models.deneme_sinavi import SINAV_TIPLERI


class DenemeSinaviForm(FlaskForm):
    ad = StringField('Sinav Adi', validators=[DataRequired(), Length(max=200)])
    sinav_tipi = SelectField('Sinav Tipi', choices=SINAV_TIPLERI, validators=[DataRequired()])
    donem = StringField('Donem', default='2025-2026', validators=[DataRequired(), Length(max=20)])
    tarih = DateField('Tarih', validators=[DataRequired()])
    sure_dakika = IntegerField('Sure (dk)', default=135,
                               validators=[DataRequired(), NumberRange(min=10, max=480)])
    hedef_seviye = StringField('Hedef Seviye',
                               validators=[Optional(), Length(max=20)],
                               description='Ornek: 8 (LGS), 12 (YKS), mezun')
    aciklama = TextAreaField('Aciklama', validators=[Optional(), Length(max=2000)])
    sablondan_olustur = SelectField(
        'Ders bloklarini otomatik olustur',
        choices=[
            ('evet', 'Evet, sablondan olustur (tavsiye edilen)'),
            ('hayir', 'Hayir, dersleri manuel ekleyecegim'),
        ],
        default='evet',
    )
    submit = SubmitField('Kaydet')


class DenemeDersiForm(FlaskForm):
    """Ders blogu ekleme/duzenleme."""
    ders_kodu = StringField('Ders Kodu (slug)',
                            validators=[DataRequired(), Length(max=40)],
                            description='Ornek: turkce, matematik, fen')
    ders_adi = StringField('Ders Adi', validators=[DataRequired(), Length(max=100)])
    soru_sayisi = IntegerField('Soru Sayisi', default=20,
                               validators=[DataRequired(), NumberRange(min=1, max=200)])
    katsayi = FloatField('Puan Katsayisi',
                         validators=[Optional(), NumberRange(min=0, max=10)],
                         description='Bos birakilirsa puan hesabinda 0 kabul edilir')
    alan = StringField('Alan Kodu',
                       validators=[Optional(), Length(max=20)],
                       description='tyt/say/soz/ea/dil/sozel/sayisal vb.')
    sira = IntegerField('Sira', default=0, validators=[Optional(), NumberRange(min=0, max=100)])
    submit = SubmitField('Kaydet')


class PdfIthalatYukleForm(FlaskForm):
    """Yayinci deneme sonuc PDF'ini yukleme formu."""
    yayinci = SelectField(
        'Yayinci / Format',
        choices=[('x_yayinlari', 'X Yayinlari (LGS Okul Net Listesi)')],
        default='x_yayinlari',
        validators=[DataRequired()],
    )
    pdf = FileField(
        'PDF Dosyasi',
        validators=[
            FileRequired('PDF dosyasi seciniz.'),
            FileAllowed(['pdf'], 'Sadece PDF dosyasi yuklenebilir.'),
        ],
    )
    submit = SubmitField('Yukle ve Onizleme')


class PdfIthalatOnaylaForm(FlaskForm):
    """Onizleme sonrasi sinav bilgilerini toplayan form."""
    sinav_adi = StringField('Sinav Adi', validators=[DataRequired(), Length(max=200)])
    donem = StringField('Donem', default='2025-2026',
                        validators=[DataRequired(), Length(max=20)])
    tarih = DateField('Sinav Tarihi', validators=[DataRequired()])
    submit = SubmitField('Onayla ve Kaydet')
