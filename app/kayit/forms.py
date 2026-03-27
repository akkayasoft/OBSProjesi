from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, DateField, IntegerField,
                     TextAreaField, SubmitField, BooleanField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from datetime import date


# === Öğrenci Formları ===

class OgrenciKayitForm(FlaskForm):
    ogrenci_no = StringField('Öğrenci No', validators=[
        DataRequired(), Length(min=1, max=20)
    ])
    tc_kimlik = StringField('TC Kimlik No', validators=[
        Optional(), Length(min=11, max=11, message='TC Kimlik No 11 haneli olmalıdır.')
    ])
    ad = StringField('Ad', validators=[DataRequired(), Length(min=2, max=100)])
    soyad = StringField('Soyad', validators=[DataRequired(), Length(min=2, max=100)])
    cinsiyet = SelectField('Cinsiyet', choices=[
        ('', '-- Seçiniz --'), ('erkek', 'Erkek'), ('kadin', 'Kadın')
    ], validators=[Optional()])
    dogum_tarihi = DateField('Doğum Tarihi', validators=[Optional()])
    dogum_yeri = StringField('Doğum Yeri', validators=[Optional(), Length(max=100)])
    kan_grubu = SelectField('Kan Grubu', choices=[
        ('', '-- Seçiniz --'), ('A+', 'A Rh+'), ('A-', 'A Rh-'),
        ('B+', 'B Rh+'), ('B-', 'B Rh-'), ('AB+', 'AB Rh+'), ('AB-', 'AB Rh-'),
        ('0+', '0 Rh+'), ('0-', '0 Rh-')
    ], validators=[Optional()])
    telefon = StringField('Öğrenci Telefon', validators=[Optional(), Length(max=20)])
    email = StringField('E-posta', validators=[Optional(), Length(max=120)])
    adres = TextAreaField('Adres', validators=[Optional(), Length(max=500)])

    # Kayıt bilgileri
    donem_id = SelectField('Dönem', coerce=int, validators=[DataRequired()])
    sube_id = SelectField('Sınıf / Şube', coerce=int, validators=[DataRequired()])

    submit = SubmitField('Kaydet')


class OgrenciDuzenleForm(FlaskForm):
    ogrenci_no = StringField('Öğrenci No', validators=[
        DataRequired(), Length(min=1, max=20)
    ])
    tc_kimlik = StringField('TC Kimlik No', validators=[
        Optional(), Length(min=11, max=11, message='TC Kimlik No 11 haneli olmalıdır.')
    ])
    ad = StringField('Ad', validators=[DataRequired(), Length(min=2, max=100)])
    soyad = StringField('Soyad', validators=[DataRequired(), Length(min=2, max=100)])
    cinsiyet = SelectField('Cinsiyet', choices=[
        ('', '-- Seçiniz --'), ('erkek', 'Erkek'), ('kadin', 'Kadın')
    ], validators=[Optional()])
    dogum_tarihi = DateField('Doğum Tarihi', validators=[Optional()])
    dogum_yeri = StringField('Doğum Yeri', validators=[Optional(), Length(max=100)])
    kan_grubu = SelectField('Kan Grubu', choices=[
        ('', '-- Seçiniz --'), ('A+', 'A Rh+'), ('A-', 'A Rh-'),
        ('B+', 'B Rh+'), ('B-', 'B Rh-'), ('AB+', 'AB Rh+'), ('AB-', 'AB Rh-'),
        ('0+', '0 Rh+'), ('0-', '0 Rh-')
    ], validators=[Optional()])
    telefon = StringField('Öğrenci Telefon', validators=[Optional(), Length(max=20)])
    email = StringField('E-posta', validators=[Optional(), Length(max=120)])
    adres = TextAreaField('Adres', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Güncelle')


class DurumDegistirForm(FlaskForm):
    durum = SelectField('Yeni Durum', choices=[
        ('aktif', 'Aktif'),
        ('mezun', 'Mezun'),
        ('nakil_giden', 'Nakil Giden'),
        ('dondurulan', 'Dondurulmuş'),
        ('kayit_silindi', 'Kayıt Silindi'),
    ], validators=[DataRequired()])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Durumu Güncelle')


# === Veli Formu ===

class VeliForm(FlaskForm):
    yakinlik = SelectField('Yakınlık', choices=[
        ('anne', 'Anne'), ('baba', 'Baba'), ('vasi', 'Vasi'), ('diger', 'Diğer')
    ], validators=[DataRequired()])
    tc_kimlik = StringField('TC Kimlik No', validators=[Optional(), Length(max=11)])
    ad = StringField('Ad', validators=[DataRequired(), Length(min=2, max=100)])
    soyad = StringField('Soyad', validators=[DataRequired(), Length(min=2, max=100)])
    telefon = StringField('Telefon', validators=[Optional(), Length(max=20)])
    email = StringField('E-posta', validators=[Optional(), Length(max=120)])
    meslek = StringField('Meslek', validators=[Optional(), Length(max=100)])
    adres = TextAreaField('Adres', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Kaydet')


# === Sınıf/Şube Formları ===

class SinifForm(FlaskForm):
    ad = StringField('Sınıf Adı', validators=[
        DataRequired(), Length(min=2, max=50)
    ], render_kw={'placeholder': 'Örn: 9. Sınıf'})
    seviye = IntegerField('Seviye', validators=[
        DataRequired(), NumberRange(min=1, max=12)
    ])
    submit = SubmitField('Kaydet')


class SubeForm(FlaskForm):
    sinif_id = SelectField('Sınıf', coerce=int, validators=[DataRequired()])
    ad = StringField('Şube Adı', validators=[
        DataRequired(), Length(min=1, max=10)
    ], render_kw={'placeholder': 'Örn: A, B, C'})
    kontenjan = IntegerField('Kontenjan', default=30, validators=[
        DataRequired(), NumberRange(min=1, max=100)
    ])
    submit = SubmitField('Kaydet')


# === Dönem Formu ===

class DonemForm(FlaskForm):
    ad = StringField('Dönem Adı', validators=[
        DataRequired(), Length(min=4, max=20)
    ], render_kw={'placeholder': 'Örn: 2025-2026'})
    baslangic_tarihi = DateField('Başlangıç Tarihi', validators=[DataRequired()])
    bitis_tarihi = DateField('Bitiş Tarihi', validators=[DataRequired()])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Kaydet')


# === Belge Formu ===

class BelgeForm(FlaskForm):
    belge_turu = SelectField('Belge Türü', choices=[
        ('nufus_cuzdani', 'Nüfus Cüzdanı Fotokopisi'),
        ('ogrenim_belgesi', 'Öğrenim Belgesi'),
        ('fotograf', 'Vesikalık Fotoğraf'),
        ('saglik_raporu', 'Sağlık Raporu'),
        ('ikametgah', 'İkametgah Belgesi'),
        ('nakil_belgesi', 'Nakil Belgesi'),
        ('diger', 'Diğer'),
    ], validators=[DataRequired()])
    teslim_edildi = BooleanField('Teslim Edildi')
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Kaydet')
