from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, FloatField, DateField, DateTimeLocalField)
from wtforms.validators import DataRequired, Optional, Length


class SaglikKaydiForm(FlaskForm):
    """Saglik kaydi formu"""
    ogrenci_id = SelectField('Öğrenci', coerce=int, validators=[
        DataRequired(message='Öğrenci seçimi zorunludur.')
    ])
    kan_grubu = SelectField('Kan Grubu', choices=[
        ('', 'Seçiniz'),
        ('A+', 'A Rh+'), ('A-', 'A Rh-'),
        ('B+', 'B Rh+'), ('B-', 'B Rh-'),
        ('AB+', 'AB Rh+'), ('AB-', 'AB Rh-'),
        ('0+', '0 Rh+'), ('0-', '0 Rh-'),
    ], validators=[Optional()])
    boy = FloatField('Boy (cm)', validators=[Optional()],
                     render_kw={'placeholder': 'Örn: 170.5'})
    kilo = FloatField('Kilo (kg)', validators=[Optional()],
                      render_kw={'placeholder': 'Örn: 65.0'})
    kronik_hastalik = TextAreaField('Kronik Hastalık', validators=[Optional()],
                                   render_kw={'placeholder': 'Varsa kronik hastalıkları yazınız', 'rows': 3})
    alerji = TextAreaField('Alerji', validators=[Optional()],
                           render_kw={'placeholder': 'Varsa alerjileri yazınız', 'rows': 3})
    surekli_ilac = TextAreaField('Sürekli İlaç', validators=[Optional()],
                                render_kw={'placeholder': 'Varsa sürekli kullandığı ilaçları yazınız', 'rows': 3})
    engel_durumu = SelectField('Engel Durumu', choices=[
        ('yok', 'Yok'),
        ('fiziksel', 'Fiziksel'),
        ('zihinsel', 'Zihinsel'),
        ('gorme', 'Görme'),
        ('isitme', 'İşitme'),
        ('diger', 'Diğer'),
    ], validators=[DataRequired()])
    ozel_not = TextAreaField('Özel Not', validators=[Optional()],
                             render_kw={'placeholder': 'Özel notlar', 'rows': 3})
    acil_kisi_adi = StringField('Acil Durumda Aranacak Kişi', validators=[
        Optional(), Length(max=100)
    ], render_kw={'placeholder': 'Ad Soyad'})
    acil_kisi_telefon = StringField('Acil Kişi Telefon', validators=[
        Optional(), Length(max=20)
    ], render_kw={'placeholder': '05XX XXX XX XX'})
    acil_kisi_yakinlik = StringField('Yakınlık Derecesi', validators=[
        Optional(), Length(max=50)
    ], render_kw={'placeholder': 'Örn: Anne, Baba, Kardeş'})
    submit = SubmitField('Kaydet')


class RevirKaydiForm(FlaskForm):
    """Revir kaydi formu"""
    ogrenci_id = SelectField('Öğrenci', coerce=int, validators=[
        DataRequired(message='Öğrenci seçimi zorunludur.')
    ])
    tarih = DateTimeLocalField('Tarih', format='%Y-%m-%dT%H:%M',
                               validators=[DataRequired(message='Tarih alanı zorunludur.')])
    sikayet = TextAreaField('Şikayet', validators=[
        DataRequired(message='Şikayet alanı zorunludur.')
    ], render_kw={'placeholder': 'Öğrencinin şikayetini yazınız', 'rows': 4})
    yapilan_islem = TextAreaField('Yapılan İşlem', validators=[
        DataRequired(message='Yapılan işlem alanı zorunludur.')
    ], render_kw={'placeholder': 'Yapılan işlemi yazınız', 'rows': 4})
    verilen_ilac = StringField('Verilen İlaç', validators=[
        Optional(), Length(max=200)
    ], render_kw={'placeholder': 'Varsa verilen ilaç'})
    sonuc = SelectField('Sonuç', choices=[
        ('sinifa_dondu', 'Sınıfa Döndü'),
        ('taburcu', 'Taburcu'),
        ('veliye_teslim', 'Veliye Teslim'),
        ('hastaneye_sevk', 'Hastaneye Sevk'),
    ], validators=[DataRequired()])
    submit = SubmitField('Kaydet')


class AsiTakipForm(FlaskForm):
    """Asi takip formu"""
    ogrenci_id = SelectField('Öğrenci', coerce=int, validators=[
        DataRequired(message='Öğrenci seçimi zorunludur.')
    ])
    asi_adi = StringField('Aşı Adı', validators=[
        DataRequired(message='Aşı adı zorunludur.'),
        Length(min=2, max=100)
    ], render_kw={'placeholder': 'Aşı adını giriniz'})
    asi_tarihi = DateField('Aşı Tarihi', validators=[
        DataRequired(message='Aşı tarihi zorunludur.')
    ])
    hatirlatma_tarihi = DateField('Hatırlatma Tarihi (Sonraki Doz)', validators=[Optional()])
    durum = SelectField('Durum', choices=[
        ('yapildi', 'Yapıldı'),
        ('bekliyor', 'Bekliyor'),
        ('gecikti', 'Gecikti'),
    ], validators=[DataRequired()])
    aciklama = TextAreaField('Açıklama', validators=[Optional()],
                             render_kw={'placeholder': 'Ek açıklama', 'rows': 3})
    submit = SubmitField('Kaydet')


class SaglikTaramasiForm(FlaskForm):
    """Saglik taramasi formu"""
    ogrenci_id = SelectField('Öğrenci', coerce=int, validators=[
        DataRequired(message='Öğrenci seçimi zorunludur.')
    ])
    tarama_tarihi = DateField('Tarama Tarihi', validators=[
        DataRequired(message='Tarama tarihi zorunludur.')
    ])
    tarama_turu = SelectField('Tarama Türü', choices=[
        ('goz', 'Göz'),
        ('kulak', 'Kulak'),
        ('dis', 'Diş'),
        ('genel', 'Genel'),
        ('boy_kilo', 'Boy/Kilo'),
        ('skolyoz', 'Skolyoz'),
    ], validators=[DataRequired()])
    sonuc = SelectField('Sonuç', choices=[
        ('normal', 'Normal'),
        ('anormal', 'Anormal'),
        ('tedavi_gerekli', 'Tedavi Gerekli'),
    ], validators=[DataRequired()])
    bulgular = TextAreaField('Bulgular', validators=[
        DataRequired(message='Bulgular alanı zorunludur.')
    ], render_kw={'placeholder': 'Tarama bulgularını yazınız', 'rows': 4})
    oneri = TextAreaField('Öneri', validators=[Optional()],
                          render_kw={'placeholder': 'Varsa önerilerinizi yazınız', 'rows': 3})
    submit = SubmitField('Kaydet')
