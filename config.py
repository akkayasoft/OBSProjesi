import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-degistirin')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'obs.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True


class ProductionConfig(Config):
    """PythonAnywhere production ayarları"""
    DEBUG = False
    # MySQL kullanmak isterseniz:
    # SQLALCHEMY_DATABASE_URI = 'mysql://KULLANICI:SIFRE@KULLANICI.mysql.pythonanywhere-services.com/KULLANICI$obs'
