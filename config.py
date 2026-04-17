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

    # === Web Push (VAPID) ===
    # Anahtarlari uretmek icin: `vapid --gen` (py-vapid). Ardindan .env'e:
    #   VAPID_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
    #   VAPID_PUBLIC_KEY=<base64url>
    #   VAPID_CLAIM_EMAIL=mailto:admin@example.com
    # Bos ise push sistemi pasif kalir.
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '').replace('\\n', '\n')
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', '')
    VAPID_CLAIM_EMAIL = os.environ.get('VAPID_CLAIM_EMAIL', 'mailto:admin@obs.local')


class ProductionConfig(Config):
    DEBUG = False
