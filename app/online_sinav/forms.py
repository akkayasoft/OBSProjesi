from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField, IntegerField,
                     FloatField, SubmitField, BooleanField, DateTimeLocalField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class OnlineSinavForm(FlaskForm):
    """Online sinav olusturma/duzenleme formu"""
    baslik = StringField('Sınav Başlığı', validators=[
        DataRequired(message='Başlık alanı zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Sınav başlığını giriniz'})
    aciklama = TextAreaField('Açıklama', validators=[
        Optional(), Length(max=1000)
    ], render_kw={'placeholder': 'Sınav açıklaması (isteğe bağlı)', 'rows': 3})
    ders_id = SelectField('Ders', coerce=int, validators=[
        DataRequired(message='Ders seçimi zorunludur.')
    ])
    sube_id = SelectField('Şube', coerce=int, validators=[Optional()])
    sure = IntegerField('Süre (dakika)', validators=[
        DataRequired(message='Süre alanı zorunludur.'),
        NumberRange(min=1, max=300, message='Süre 1-300 dakika arasında olmalıdır.')
    ], render_kw={'placeholder': 'Örn: 60'})
    baslangic_zamani = DateTimeLocalField('Başlangıç Zamanı', format='%Y-%m-%dT%H:%M',
                                          validators=[DataRequired(message='Başlangıç zamanı zorunludur.')])
    bitis_zamani = DateTimeLocalField('Bitiş Zamanı', format='%Y-%m-%dT%H:%M',
                                      validators=[DataRequired(message='Bitiş zamanı zorunludur.')])
    sinav_turu = SelectField('Sınav Türü', choices=[
        ('test', 'Test'),
        ('klasik', 'Klasik'),
        ('karisik', 'Karışık'),
    ], validators=[DataRequired()])
    zorluk = SelectField('Zorluk', choices=[
        ('kolay', 'Kolay'),
        ('orta', 'Orta'),
        ('zor', 'Zor'),
    ], validators=[DataRequired()])
    toplam_puan = FloatField('Toplam Puan', validators=[
        DataRequired(message='Toplam puan zorunludur.'),
        NumberRange(min=1)
    ], default=100)
    gecme_puani = FloatField('Geçme Puanı', validators=[
        DataRequired(message='Geçme puanı zorunludur.'),
        NumberRange(min=0)
    ], default=50)
    sorulari_karistir = BooleanField('Soruları Karıştır')
    secenekleri_karistir = BooleanField('Seçenekleri Karıştır')
    sonuclari_goster = BooleanField('Sonuçları Öğrencilere Göster', default=True)
    submit = SubmitField('Kaydet')


class SoruForm(FlaskForm):
    """Sinav sorusu formu"""
    soru_metni = TextAreaField('Soru Metni', validators=[
        DataRequired(message='Soru metni zorunludur.')
    ], render_kw={'placeholder': 'Soruyu giriniz', 'rows': 4})
    soru_turu = SelectField('Soru Türü', choices=[
        ('coktan_secmeli', 'Çoktan Seçmeli'),
        ('dogru_yanlis', 'Doğru/Yanlış'),
        ('klasik', 'Klasik'),
        ('bosluk_doldurma', 'Boşluk Doldurma'),
    ], validators=[DataRequired()])
    puan = FloatField('Puan', validators=[
        DataRequired(message='Puan alanı zorunludur.'),
        NumberRange(min=0.1)
    ], render_kw={'placeholder': 'Örn: 10'})
    zorluk = SelectField('Zorluk', choices=[
        ('kolay', 'Kolay'),
        ('orta', 'Orta'),
        ('zor', 'Zor'),
    ], validators=[DataRequired()])
    aciklama = TextAreaField('Açıklama (sınav sonrası gösterilir)', validators=[
        Optional(), Length(max=500)
    ], render_kw={'placeholder': 'Cevap açıklaması (isteğe bağlı)', 'rows': 2})
    submit = SubmitField('Kaydet')


class SoruSecenegiForm(FlaskForm):
    """Soru secenegi formu"""
    secenek_metni = StringField('Seçenek Metni', validators=[
        DataRequired(message='Seçenek metni zorunludur.')
    ])
    dogru_mu = BooleanField('Doğru Cevap')
