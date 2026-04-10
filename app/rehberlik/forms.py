from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, IntegerField, DateField, DateTimeLocalField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class GorusmeForm(FlaskForm):
    """Rehberlik gorusmesi formu"""
    ogrenci_id = SelectField('Ogrenci', coerce=int,
                             validators=[DataRequired(message='Ogrenci secimi zorunludur.')])
    gorusme_tarihi = DateTimeLocalField('Gorusme Tarihi', format='%Y-%m-%dT%H:%M',
                                        validators=[DataRequired(message='Gorusme tarihi zorunludur.')])
    gorusme_turu = SelectField('Gorusme Turu', choices=[
        ('bireysel', 'Bireysel'),
        ('grup', 'Grup'),
        ('veli', 'Veli'),
        ('kriz', 'Kriz'),
    ], validators=[DataRequired()])
    konu = StringField('Konu', validators=[
        DataRequired(message='Konu alani zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Gorusme konusunu giriniz'})
    icerik = TextAreaField('Icerik', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Gorusme icerigini giriniz', 'rows': 5})
    sonuc_ve_oneri = TextAreaField('Sonuc ve Oneriler', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Sonuc ve onerileri giriniz', 'rows': 4})
    gizlilik_seviyesi = SelectField('Gizlilik Seviyesi', choices=[
        ('normal', 'Normal'),
        ('gizli', 'Gizli'),
        ('cok_gizli', 'Cok Gizli'),
    ], validators=[DataRequired()])
    durum = SelectField('Durum', choices=[
        ('planlandi', 'Planlandi'),
        ('tamamlandi', 'Tamamlandi'),
        ('iptal', 'Iptal'),
    ], validators=[DataRequired()])
    submit = SubmitField('Kaydet')


class OgrenciProfilForm(FlaskForm):
    """Ogrenci rehberlik profil formu"""
    ogrenci_id = SelectField('Ogrenci', coerce=int,
                             validators=[DataRequired(message='Ogrenci secimi zorunludur.')])
    aile_durumu = SelectField('Aile Durumu', choices=[
        ('normal', 'Normal'),
        ('bosanmis', 'Bosanmis'),
        ('tek_ebeveyn', 'Tek Ebeveyn'),
        ('vefat', 'Vefat'),
        ('diger', 'Diger'),
    ], validators=[DataRequired()])
    kardes_sayisi = IntegerField('Kardes Sayisi', validators=[
        Optional(), NumberRange(min=0, max=20)
    ], default=0)
    ekonomik_durum = SelectField('Ekonomik Durum', choices=[
        ('iyi', 'Iyi'),
        ('orta', 'Orta'),
        ('dusuk', 'Dusuk'),
    ], validators=[Optional()])
    saglik_durumu = TextAreaField('Saglik Durumu', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Saglik durumu hakkinda bilgi', 'rows': 3})
    ozel_not = TextAreaField('Ozel Not', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Ozel notlar', 'rows': 3})
    ilgi_alanlari = TextAreaField('Ilgi Alanlari', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Ilgi alanlari', 'rows': 3})
    guclu_yonler = TextAreaField('Guclu Yonler', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Guclu yonleri', 'rows': 3})
    gelistirilecek_yonler = TextAreaField('Gelistirilecek Yonler', validators=[
        Optional(), Length(max=2000)
    ], render_kw={'placeholder': 'Gelistirilecek yonleri', 'rows': 3})
    submit = SubmitField('Kaydet')



class VeliGorusmesiForm(FlaskForm):
    """Veli gorusmesi formu"""
    ogrenci_id = SelectField('Ogrenci', coerce=int,
                             validators=[DataRequired(message='Ogrenci secimi zorunludur.')])
    veli_adi = StringField('Veli Adi', validators=[
        DataRequired(message='Veli adi zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Veli adini giriniz'})
    veli_telefon = StringField('Veli Telefon', validators=[
        Optional(), Length(max=20)
    ], render_kw={'placeholder': 'Telefon numarasi'})
    gorusme_tarihi = DateTimeLocalField('Gorusme Tarihi', format='%Y-%m-%dT%H:%M',
                                        validators=[DataRequired(message='Gorusme tarihi zorunludur.')])
    gorusme_turu = SelectField('Gorusme Turu', choices=[
        ('yuz_yuze', 'Yuz Yuze'),
        ('telefon', 'Telefon'),
        ('online', 'Online'),
    ], validators=[DataRequired()])
    konu = StringField('Konu', validators=[
        DataRequired(message='Konu alani zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Gorusme konusu'})
    icerik = TextAreaField('Icerik', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Gorusme icerigini giriniz', 'rows': 5})
    sonuc = TextAreaField('Sonuc', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Gorusme sonucunu giriniz', 'rows': 4})
    submit = SubmitField('Kaydet')


class RehberlikPlaniForm(FlaskForm):
    """Rehberlik plani formu"""
    ogrenci_id = SelectField('Ogrenci', coerce=int,
                             validators=[DataRequired(message='Ogrenci secimi zorunludur.')])
    baslik = StringField('Baslik', validators=[
        DataRequired(message='Baslik alani zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Plan basligini giriniz'})
    hedefler = TextAreaField('Hedefler', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Hedefleri giriniz', 'rows': 4})
    uygulanacak_yontemler = TextAreaField('Uygulanacak Yontemler', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Uygulanacak yontemleri giriniz', 'rows': 4})
    baslangic_tarihi = DateField('Baslangic Tarihi',
                                  validators=[DataRequired(message='Baslangic tarihi zorunludur.')])
    bitis_tarihi = DateField('Bitis Tarihi', validators=[Optional()])
    durum = SelectField('Durum', choices=[
        ('aktif', 'Aktif'),
        ('tamamlandi', 'Tamamlandi'),
        ('beklemede', 'Beklemede'),
    ], validators=[DataRequired()])
    degerlendirme = TextAreaField('Degerlendirme', validators=[
        Optional(), Length(max=5000)
    ], render_kw={'placeholder': 'Degerlendirme notlari', 'rows': 3})
    submit = SubmitField('Kaydet')
