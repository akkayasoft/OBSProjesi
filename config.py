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

    # === Multi-tenant (SaaS) ayarlari ===
    # Flag kapaliysa tek-kiracili klasik mod. Aciksa master DB + subdomain
    # cozumlemesi aktif olur, istegi dogru tenant DB'sine yonlendirir.
    MULTITENANT_ENABLED = os.environ.get('MULTITENANT_ENABLED', '0') in ('1', 'true', 'True')

    # Ana domain (ornek: obs.akkayasoft.com). *.obs.akkayasoft.com icin
    # subdomain'den tenant slug cikarilir.
    TENANT_ROOT_DOMAIN = os.environ.get('TENANT_ROOT_DOMAIN', '')

    # Root domain'de veya bilinmeyen host'ta dusulecek default slug.
    # Bos birakilirsa root domain 404 doner.
    TENANT_DEFAULT_SLUG = os.environ.get('TENANT_DEFAULT_SLUG', '')

    # Master DB: tenants tablosu burada durur (tum kurumlardan bagimsiz).
    # Ornek: postgresql://obs:pass@localhost/obs_master
    MASTER_DATABASE_URL = _normalize_db_url(os.environ.get('MASTER_DATABASE_URL', '')) or ''

    # Tenant DB URL template'i — {db_name} yer tutucusu substitue edilir.
    # Ornek: postgresql://obs:pass@localhost/{db_name}
    TENANT_DATABASE_URL_TEMPLATE = os.environ.get('TENANT_DATABASE_URL_TEMPLATE', '')

    # CLI `tenant create --create-db` icin admin baglantisi (CREATE DATABASE yetkili).
    # Bos ise MASTER_DATABASE_URL kullanilir.
    TENANT_ADMIN_DATABASE_URL = _normalize_db_url(os.environ.get('TENANT_ADMIN_DATABASE_URL', '')) or ''

    MASTER_DB_POOL_SIZE = int(os.environ.get('MASTER_DB_POOL_SIZE', '5'))
    TENANT_DB_POOL_SIZE = int(os.environ.get('TENANT_DB_POOL_SIZE', '5'))


class ProductionConfig(Config):
    DEBUG = False
