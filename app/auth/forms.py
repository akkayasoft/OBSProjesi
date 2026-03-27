from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    username = StringField('Kullanıcı Adı', validators=[
        DataRequired(message='Kullanıcı adı gereklidir.'),
        Length(min=3, max=80)
    ])
    password = PasswordField('Şifre', validators=[
        DataRequired(message='Şifre gereklidir.')
    ])
    remember_me = BooleanField('Beni Hatırla')
    submit = SubmitField('Giriş Yap')
