import os

basedir = os.path.abspath(os.path.dirname(__file__))


def _normalize_db_url(url: str) -> str:
    # Render/Heroku, eski "postgres://" şemasını verebilir; SQLAlchemy 2.x "postgresql://" ister.
    if url and url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    return url


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-degistirin')
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.environ.get('DATABASE_URL') or '') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'obs.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    UPLOAD_FOLDER = os.path.join(basedir, 'instance', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_BELGE_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'webp', 'tiff', 'bmp'}


class ProductionConfig(Config):
    DEBUG = False
