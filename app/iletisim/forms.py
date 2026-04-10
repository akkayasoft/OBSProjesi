from flask_wtf import FlaskForm
from wtforms import (StringField, SelectField, TextAreaField,
                     SubmitField)
from wtforms.validators import DataRequired, Optional, Length, Email


class MesajForm(FlaskForm):
    """Mesaj oluşturma formu"""
    alici_id = SelectField('Alıcı', coerce=int, validators=[
        DataRequired(message='Alıcı seçimi zorunludur.')
    ])
    konu = StringField('Konu', validators=[
        DataRequired(message='Konu alanı zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Mesaj konusunu giriniz'})
    icerik = TextAreaField('Mesaj', validators=[
        DataRequired(message='Mesaj içeriği zorunludur.')
    ], render_kw={'placeholder': 'Mesajınızı yazınız...', 'rows': 6})
    submit = SubmitField('Gönder')


class TopluMesajForm(FlaskForm):
    """Toplu mesaj oluşturma formu"""
    baslik = StringField('Başlık', validators=[
        DataRequired(message='Başlık alanı zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Mesaj başlığını giriniz'})
    icerik = TextAreaField('İçerik', validators=[
        DataRequired(message='İçerik alanı zorunludur.')
    ], render_kw={'placeholder': 'Mesaj içeriğini giriniz...', 'rows': 6})
    hedef_grup = SelectField('Hedef Grup', choices=[
        ('tumu', 'Tümü'),
        ('ogretmenler', 'Öğretmenler'),
        ('veliler', 'Veliler'),
        ('personel', 'Personel'),
        ('sinif', 'Sınıf'),
    ], validators=[DataRequired()])
    hedef_sinif = SelectField('Hedef Sınıf', choices=[('', 'Sınıf seçiniz')],
                              validators=[Optional()])
    gonderim_turu = SelectField('Gönderim Türü', choices=[
        ('sistem', 'Sistem Bildirimi'),
        ('sms', 'SMS'),
        ('email', 'E-Posta'),
    ], validators=[DataRequired()])
    submit = SubmitField('Oluştur')


class MesajSablonuForm(FlaskForm):
    """Mesaj şablonu oluşturma/düzenleme formu"""
    baslik = StringField('Başlık', validators=[
        DataRequired(message='Başlık alanı zorunludur.'),
        Length(min=2, max=200)
    ], render_kw={'placeholder': 'Şablon başlığını giriniz'})
    icerik = TextAreaField('İçerik', validators=[
        DataRequired(message='İçerik alanı zorunludur.')
    ], render_kw={'placeholder': 'Şablon içeriğini giriniz...', 'rows': 6})
    kategori = SelectField('Kategori', choices=[
        ('genel', 'Genel'),
        ('devamsizlik', 'Devamsızlık'),
        ('odeme', 'Ödeme'),
        ('toplanti', 'Toplantı'),
        ('sinav', 'Sınav'),
        ('diger', 'Diğer'),
    ], validators=[DataRequired()])
    submit = SubmitField('Kaydet')


class IletisimDefteriForm(FlaskForm):
    """İletişim defteri oluşturma/düzenleme formu"""
    ad = StringField('Ad', validators=[
        DataRequired(message='Ad alanı zorunludur.'),
        Length(min=2, max=100)
    ], render_kw={'placeholder': 'Ad'})
    soyad = StringField('Soyad', validators=[
        DataRequired(message='Soyad alanı zorunludur.'),
        Length(min=2, max=100)
    ], render_kw={'placeholder': 'Soyad'})
    telefon = StringField('Telefon', validators=[
        DataRequired(message='Telefon alanı zorunludur.'),
        Length(min=10, max=20)
    ], render_kw={'placeholder': '05XX XXX XX XX'})
    email = StringField('E-Posta', validators=[
        Optional(), Email(message='Geçerli bir e-posta adresi giriniz.')
    ], render_kw={'placeholder': 'ornek@email.com'})
    kurum = StringField('Kurum', validators=[
        Optional(), Length(max=200)
    ], render_kw={'placeholder': 'Kurum adı (isteğe bağlı)'})
    gorev = StringField('Görev', validators=[
        Optional(), Length(max=200)
    ], render_kw={'placeholder': 'Görev (isteğe bağlı)'})
    kategori = SelectField('Kategori', choices=[
        ('veli', 'Veli'),
        ('kurum', 'Kurum'),
        ('diger', 'Diğer'),
    ], validators=[DataRequired()])
    ogrenci_id = SelectField('Öğrenci', coerce=int, choices=[(0, 'Seçiniz (isteğe bağlı)')],
                             validators=[Optional()])
    yakinlik = SelectField('Yakınlık', choices=[
        ('', 'Seçiniz'),
        ('anne', 'Anne'),
        ('baba', 'Baba'),
        ('vasi', 'Vasi'),
        ('diger', 'Diğer'),
    ], validators=[Optional()])
    submit = SubmitField('Kaydet')
