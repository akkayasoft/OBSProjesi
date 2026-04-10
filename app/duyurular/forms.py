from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField, BooleanField, DateTimeLocalField)
from wtforms.validators import DataRequired, Optional, Length


class DuyuruForm(FlaskForm):
    """Duyuru oluşturma/düzenleme formu"""
    baslik = StringField('Başlık', validators=[
        DataRequired(message='Başlık alanı zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Duyuru başlığını giriniz'})
    icerik = TextAreaField('İçerik', validators=[
        DataRequired(message='İçerik alanı zorunludur.')
    ], render_kw={'placeholder': 'Duyuru içeriğini giriniz', 'rows': 6})
    kategori = SelectField('Kategori', choices=[
        ('genel', 'Genel'),
        ('akademik', 'Akademik'),
        ('idari', 'İdari'),
        ('etkinlik', 'Etkinlik'),
        ('acil', 'Acil'),
    ], validators=[DataRequired()])
    oncelik = SelectField('Öncelik', choices=[
        ('normal', 'Normal'),
        ('onemli', 'Önemli'),
        ('acil', 'Acil'),
    ], validators=[DataRequired()])
    hedef_kitle = SelectField('Hedef Kitle', choices=[
        ('tumu', 'Tümü'),
        ('ogretmenler', 'Öğretmenler'),
        ('ogrenciler', 'Öğrenciler'),
        ('veliler', 'Veliler'),
        ('personel', 'Personel'),
    ], validators=[DataRequired()])
    bitis_tarihi = DateTimeLocalField('Bitiş Tarihi', format='%Y-%m-%dT%H:%M',
                                      validators=[Optional()])
    sabitlenmis = BooleanField('Sabitlenmiş')
    submit = SubmitField('Kaydet')


class EtkinlikForm(FlaskForm):
    """Etkinlik oluşturma/düzenleme formu"""
    baslik = StringField('Başlık', validators=[
        DataRequired(message='Başlık alanı zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Etkinlik başlığını giriniz'})
    aciklama = TextAreaField('Açıklama', validators=[
        Optional(), Length(max=1000)
    ], render_kw={'placeholder': 'Etkinlik açıklaması', 'rows': 4})
    tur = SelectField('Tür', choices=[
        ('toplanti', 'Toplantı'),
        ('sinav', 'Sınav'),
        ('kutlama', 'Kutlama'),
        ('gezi', 'Gezi'),
        ('spor', 'Spor'),
        ('diger', 'Diğer'),
    ], validators=[DataRequired()])
    baslangic_tarihi = DateTimeLocalField('Başlangıç Tarihi', format='%Y-%m-%dT%H:%M',
                                          validators=[DataRequired(message='Başlangıç tarihi zorunludur.')])
    bitis_tarihi = DateTimeLocalField('Bitiş Tarihi', format='%Y-%m-%dT%H:%M',
                                      validators=[DataRequired(message='Bitiş tarihi zorunludur.')])
    konum = StringField('Konum', validators=[
        Optional(), Length(max=200)
    ], render_kw={'placeholder': 'Etkinlik konumu'})
    renk = StringField('Renk', validators=[DataRequired()],
                       render_kw={'type': 'color', 'value': '#3498db'})
    tum_gun = BooleanField('Tüm Gün')
    submit = SubmitField('Kaydet')


class HatirlatmaForm(FlaskForm):
    """Hatırlatma oluşturma formu"""
    baslik = StringField('Başlık', validators=[
        DataRequired(message='Başlık alanı zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Hatırlatma başlığını giriniz'})
    aciklama = TextAreaField('Açıklama', validators=[
        Optional(), Length(max=500)
    ], render_kw={'placeholder': 'Açıklama (isteğe bağlı)', 'rows': 3})
    tarih = DateTimeLocalField('Tarih', format='%Y-%m-%dT%H:%M',
                               validators=[DataRequired(message='Tarih alanı zorunludur.')])
    oncelik = SelectField('Öncelik', choices=[
        ('dusuk', 'Düşük'),
        ('normal', 'Normal'),
        ('yuksek', 'Yüksek'),
    ], validators=[DataRequired()])
    submit = SubmitField('Kaydet')
