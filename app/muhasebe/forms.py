from flask_wtf import FlaskForm
from wtforms import (StringField, DecimalField, TextAreaField, SelectField,
                     DateField, IntegerField, SubmitField)
from wtforms.validators import DataRequired, NumberRange, Optional, Length
from datetime import date


# === Gelir/Gider Formları ===

class GelirGiderForm(FlaskForm):
    tur = SelectField('Tür', choices=[('gelir', 'Gelir'), ('gider', 'Gider')],
                      validators=[DataRequired()])
    kategori_id = SelectField('Kategori', coerce=int, validators=[DataRequired()])
    tutar = DecimalField('Tutar (₺)', places=2, validators=[
        DataRequired(message='Tutar gereklidir.'),
        NumberRange(min=0.01, message='Tutar 0\'dan büyük olmalıdır.')
    ])
    tarih = DateField('Tarih', default=date.today, validators=[DataRequired()])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    belge_no = StringField('Belge No', validators=[Optional(), Length(max=50)])
    banka_hesap_id = SelectField('Banka Hesabı', coerce=int, validators=[Optional()])
    submit = SubmitField('Kaydet')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.banka_hesap_id.choices = [(0, '-- Seçiniz (Opsiyonel) --')]


class KategoriForm(FlaskForm):
    ad = StringField('Kategori Adı', validators=[
        DataRequired(message='Kategori adı gereklidir.'),
        Length(min=2, max=100)
    ])
    tur = SelectField('Tür', choices=[('gelir', 'Gelir'), ('gider', 'Gider')],
                      validators=[DataRequired()])
    submit = SubmitField('Kaydet')


# === Öğrenci Ödeme Formları ===


class OdemePlaniForm(FlaskForm):
    donem = StringField('Dönem', validators=[
        DataRequired(), Length(min=4, max=20)
    ], default='2025-2026')
    toplam_tutar = DecimalField('Toplam Tutar (₺)', places=2, validators=[
        DataRequired(), NumberRange(min=0.01)
    ])
    indirim_tutar = DecimalField('İndirim / Burs (₺)', places=2, default=0, validators=[
        Optional(), NumberRange(min=0)
    ])
    indirim_aciklama = StringField('İndirim Açıklaması', validators=[
        Optional(), Length(max=200)
    ])
    taksit_sayisi = IntegerField('Taksit Sayısı', validators=[
        DataRequired(), NumberRange(min=1, max=12)
    ])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Ödeme Planı Oluştur')


class OdemeForm(FlaskForm):
    tutar = DecimalField('Ödenen Tutar (₺)', places=2, validators=[
        DataRequired(), NumberRange(min=0.01)
    ])
    odeme_turu = SelectField('Ödeme Türü', choices=[
        ('nakit', 'Nakit'),
        ('havale', 'Havale/EFT'),
        ('kredi_karti', 'Kredi Kartı'),
        ('eft', 'EFT')
    ], validators=[DataRequired()])
    banka_hesap_id = SelectField('Banka Hesabı', coerce=int, validators=[Optional()])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Ödemeyi Kaydet')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.banka_hesap_id.choices = [(0, '-- Seçiniz (Opsiyonel) --')]


# === Personel Formları ===

class PersonelForm(FlaskForm):
    sicil_no = StringField('Sicil No', validators=[DataRequired(), Length(min=1, max=20)])
    ad = StringField('Ad', validators=[DataRequired(), Length(min=2, max=100)])
    soyad = StringField('Soyad', validators=[DataRequired(), Length(min=2, max=100)])
    pozisyon = StringField('Pozisyon', validators=[Optional(), Length(max=100)])
    maas = DecimalField('Maaş (₺)', places=2, validators=[Optional(), NumberRange(min=0)])
    submit = SubmitField('Kaydet')


class PersonelOdemeForm(FlaskForm):
    donem = StringField('Dönem (YYYY-MM)', validators=[
        DataRequired(), Length(min=6, max=20)
    ])
    tutar = DecimalField('Tutar (₺)', places=2, validators=[
        DataRequired(), NumberRange(min=0.01)
    ])
    odeme_turu = SelectField('Ödeme Türü', choices=[
        ('havale', 'Havale/EFT'),
        ('nakit', 'Nakit'),
        ('eft', 'EFT')
    ], validators=[DataRequired()])
    banka_hesap_id = SelectField('Banka Hesabı', coerce=int, validators=[Optional()])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Ödemeyi Kaydet')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.banka_hesap_id.choices = [(0, '-- Seçiniz (Opsiyonel) --')]


# === Banka Formları ===

class BankaHesapForm(FlaskForm):
    banka_adi = StringField('Banka Adı', validators=[
        DataRequired(), Length(min=2, max=100)
    ])
    hesap_adi = StringField('Hesap Adı', validators=[
        DataRequired(), Length(min=2, max=100)
    ])
    iban = StringField('IBAN', validators=[Optional(), Length(max=34)])
    hesap_no = StringField('Hesap No', validators=[Optional(), Length(max=30)])
    bakiye = DecimalField('Açılış Bakiyesi (₺)', places=2, default=0,
                          validators=[Optional()])
    submit = SubmitField('Kaydet')


class TransferForm(FlaskForm):
    kaynak_hesap_id = SelectField('Kaynak Hesap', coerce=int,
                                  validators=[DataRequired()])
    hedef_hesap_id = SelectField('Hedef Hesap', coerce=int,
                                 validators=[DataRequired()])
    tutar = DecimalField('Tutar (₺)', places=2, validators=[
        DataRequired(), NumberRange(min=0.01)
    ])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Transfer Yap')
