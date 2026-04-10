from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, BooleanField, IntegerField, DateField)
from wtforms.validators import DataRequired, Email, Length, Optional


class KurumForm(FlaskForm):
    """Kurum bilgileri formu"""
    ad = StringField('Kurum Adi', validators=[
        DataRequired(message='Kurum adi zorunludur.'),
        Length(max=200)
    ], render_kw={'placeholder': 'Kurum adini giriniz'})
    kisa_ad = StringField('Kisa Ad', validators=[
        Optional(), Length(max=50)
    ], render_kw={'placeholder': 'Kisaltma'})
    kurum_turu = SelectField('Kurum Turu', choices=[
        ('ilkokul', 'Ilkokul'),
        ('ortaokul', 'Ortaokul'),
        ('lise', 'Lise'),
        ('kolej', 'Kolej'),
        ('kurs', 'Kurs'),
    ], validators=[DataRequired(message='Kurum turu zorunludur.')])
    kurum_kodu = StringField('Kurum Kodu', validators=[
        Optional(), Length(max=50)
    ], render_kw={'placeholder': 'Kurum kodu'})
    telefon = StringField('Telefon', validators=[
        Optional(), Length(max=20)
    ], render_kw={'placeholder': 'Telefon numarasi'})
    fax = StringField('Fax', validators=[
        Optional(), Length(max=20)
    ], render_kw={'placeholder': 'Fax numarasi'})
    email = StringField('E-posta', validators=[
        Optional(), Email(message='Gecerli bir e-posta giriniz.'),
        Length(max=120)
    ], render_kw={'placeholder': 'E-posta adresi'})
    web_sitesi = StringField('Web Sitesi', validators=[
        Optional(), Length(max=200)
    ], render_kw={'placeholder': 'https://...'})
    adres = TextAreaField('Adres', validators=[
        Optional()
    ], render_kw={'placeholder': 'Adres', 'rows': 3})
    il = StringField('Il', validators=[
        Optional(), Length(max=50)
    ], render_kw={'placeholder': 'Il'})
    ilce = StringField('Ilce', validators=[
        Optional(), Length(max=50)
    ], render_kw={'placeholder': 'Ilce'})
    posta_kodu = StringField('Posta Kodu', validators=[
        Optional(), Length(max=10)
    ], render_kw={'placeholder': 'Posta kodu'})
    vergi_dairesi = StringField('Vergi Dairesi', validators=[
        Optional(), Length(max=100)
    ], render_kw={'placeholder': 'Vergi dairesi'})
    vergi_no = StringField('Vergi No', validators=[
        Optional(), Length(max=20)
    ], render_kw={'placeholder': 'Vergi numarasi'})
    mudur_adi = StringField('Mudur Adi', validators=[
        Optional(), Length(max=150)
    ], render_kw={'placeholder': 'Mudur adi'})
    mudur_telefon = StringField('Mudur Telefon', validators=[
        Optional(), Length(max=20)
    ], render_kw={'placeholder': 'Mudur telefonu'})
    logo_url = StringField('Logo URL', validators=[
        Optional(), Length(max=300)
    ], render_kw={'placeholder': 'Logo adresi'})
    slogan = StringField('Slogan', validators=[
        Optional(), Length(max=300)
    ], render_kw={'placeholder': 'Kurum slogani'})
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')


class OgretimYiliForm(FlaskForm):
    """Ogretim yili formu"""
    ad = StringField('Ogretim Yili Adi', validators=[
        DataRequired(message='Ogretim yili adi zorunludur.'),
        Length(max=50)
    ], render_kw={'placeholder': 'Ornek: 2025-2026'})
    baslangic_tarihi = DateField('Baslangic Tarihi', validators=[
        DataRequired(message='Baslangic tarihi zorunludur.')
    ])
    bitis_tarihi = DateField('Bitis Tarihi', validators=[
        DataRequired(message='Bitis tarihi zorunludur.')
    ])
    yariyil_baslangic = DateField('Yariyil Baslangic', validators=[
        Optional()
    ])
    yariyil_bitis = DateField('Yariyil Bitis', validators=[
        Optional()
    ])
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')


class TatilForm(FlaskForm):
    """Tatil formu"""
    ad = StringField('Tatil Adi', validators=[
        DataRequired(message='Tatil adi zorunludur.'),
        Length(max=150)
    ], render_kw={'placeholder': 'Tatil adini giriniz'})
    baslangic_tarihi = DateField('Baslangic Tarihi', validators=[
        DataRequired(message='Baslangic tarihi zorunludur.')
    ])
    bitis_tarihi = DateField('Bitis Tarihi', validators=[
        DataRequired(message='Bitis tarihi zorunludur.')
    ])
    tur = SelectField('Tur', choices=[
        ('resmi_tatil', 'Resmi Tatil'),
        ('ara_tatil', 'Ara Tatil'),
        ('sinav_haftasi', 'Sinav Haftasi'),
        ('diger', 'Diger'),
    ], validators=[DataRequired(message='Tur secimi zorunludur.')])
    ogretim_yili_id = SelectField('Ogretim Yili', coerce=int, validators=[
        DataRequired(message='Ogretim yili zorunludur.')
    ])
    submit = SubmitField('Kaydet')


class DerslikForm(FlaskForm):
    """Derslik formu"""
    ad = StringField('Derslik Adi', validators=[
        DataRequired(message='Derslik adi zorunludur.'),
        Length(max=50)
    ], render_kw={'placeholder': 'Ornek: A-101'})
    kat = IntegerField('Kat', validators=[
        Optional()
    ], render_kw={'placeholder': 'Kat numarasi'})
    kapasite = IntegerField('Kapasite', validators=[
        Optional()
    ], render_kw={'placeholder': 'Ogrenci kapasitesi'})
    tur = SelectField('Tur', choices=[
        ('sinif', 'Sinif'),
        ('lab', 'Laboratuvar'),
        ('spor_salonu', 'Spor Salonu'),
        ('konferans', 'Konferans Salonu'),
        ('kutuphane', 'Kutuphane'),
        ('diger', 'Diger'),
    ], validators=[DataRequired(message='Tur secimi zorunludur.')])
    donanim = TextAreaField('Donanim Bilgisi', validators=[
        Optional()
    ], render_kw={'placeholder': 'Mevcut donanim ve ekipmanlar', 'rows': 3})
    aktif = BooleanField('Aktif', default=True)
    submit = SubmitField('Kaydet')
