from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, DateField, DecimalField,
                     TextAreaField, SubmitField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


# === Personel Formları ===

class PersonelForm(FlaskForm):
    sicil_no = StringField('Sicil No', validators=[
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
    telefon = StringField('Telefon', validators=[Optional(), Length(max=20)])
    email = StringField('E-posta', validators=[Optional(), Length(max=120)])
    adres = TextAreaField('Adres', validators=[Optional(), Length(max=500)])

    # İş bilgileri
    pozisyon = StringField('Pozisyon / Unvan', validators=[
        Optional(), Length(max=100)
    ], render_kw={'placeholder': 'Örn: Matematik Öğretmeni'})
    departman = SelectField('Departman', choices=[
        ('', '-- Seçiniz --'),
        ('Matematik', 'Matematik'),
        ('Fen Bilimleri', 'Fen Bilimleri'),
        ('Türkçe', 'Türkçe'),
        ('Sosyal Bilimler', 'Sosyal Bilimler'),
        ('Yabancı Dil', 'Yabancı Dil'),
        ('Beden Eğitimi', 'Beden Eğitimi'),
        ('Görsel Sanatlar', 'Görsel Sanatlar'),
        ('Müzik', 'Müzik'),
        ('Bilişim', 'Bilişim'),
        ('Rehberlik', 'Rehberlik'),
        ('İdari', 'İdari'),
        ('Destek', 'Destek'),
        ('Diğer', 'Diğer'),
    ], validators=[Optional()])
    calisma_turu = SelectField('Çalışma Türü', choices=[
        ('tam_zamanli', 'Tam Zamanlı'),
        ('yari_zamanli', 'Yarı Zamanlı'),
        ('sozlesmeli', 'Sözleşmeli'),
    ], validators=[DataRequired()])
    maas = DecimalField('Maaş (₺)', validators=[Optional(), NumberRange(min=0)], places=2)
    ise_baslama_tarihi = DateField('İşe Başlama Tarihi', validators=[Optional()])

    submit = SubmitField('Kaydet')


class PersonelDuzenleForm(FlaskForm):
    sicil_no = StringField('Sicil No', validators=[
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
    telefon = StringField('Telefon', validators=[Optional(), Length(max=20)])
    email = StringField('E-posta', validators=[Optional(), Length(max=120)])
    adres = TextAreaField('Adres', validators=[Optional(), Length(max=500)])

    pozisyon = StringField('Pozisyon / Unvan', validators=[Optional(), Length(max=100)])
    departman = SelectField('Departman', choices=[
        ('', '-- Seçiniz --'),
        ('Matematik', 'Matematik'),
        ('Fen Bilimleri', 'Fen Bilimleri'),
        ('Türkçe', 'Türkçe'),
        ('Sosyal Bilimler', 'Sosyal Bilimler'),
        ('Yabancı Dil', 'Yabancı Dil'),
        ('Beden Eğitimi', 'Beden Eğitimi'),
        ('Görsel Sanatlar', 'Görsel Sanatlar'),
        ('Müzik', 'Müzik'),
        ('Bilişim', 'Bilişim'),
        ('Rehberlik', 'Rehberlik'),
        ('İdari', 'İdari'),
        ('Destek', 'Destek'),
        ('Diğer', 'Diğer'),
    ], validators=[Optional()])
    calisma_turu = SelectField('Çalışma Türü', choices=[
        ('tam_zamanli', 'Tam Zamanlı'),
        ('yari_zamanli', 'Yarı Zamanlı'),
        ('sozlesmeli', 'Sözleşmeli'),
    ], validators=[DataRequired()])
    maas = DecimalField('Maaş (₺)', validators=[Optional(), NumberRange(min=0)], places=2)
    ise_baslama_tarihi = DateField('İşe Başlama Tarihi', validators=[Optional()])
    ise_bitis_tarihi = DateField('İşten Ayrılma Tarihi', validators=[Optional()])

    submit = SubmitField('Güncelle')


# === İzin Formu ===

class IzinForm(FlaskForm):
    personel_id = SelectField('Personel', coerce=int, validators=[DataRequired()])
    izin_turu = SelectField('İzin Türü', choices=[
        ('yillik', 'Yıllık İzin'),
        ('saglik', 'Sağlık İzni'),
        ('mazeret', 'Mazeret İzni'),
        ('ucretsiz', 'Ücretsiz İzin'),
        ('idari', 'İdari İzin'),
    ], validators=[DataRequired()])
    baslangic_tarihi = DateField('Başlangıç Tarihi', validators=[DataRequired()])
    bitis_tarihi = DateField('Bitiş Tarihi', validators=[DataRequired()])
    aciklama = TextAreaField('Açıklama', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Kaydet')
