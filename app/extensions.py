from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from app.tenancy.session import TenantAwareSession


# db.session custom Session sinifiyla olusturulur — multi-tenant kapaliysa
# zararsiz (parent'a duser), aciksa g.tenant_engine'e baglanir.
db = SQLAlchemy(session_options={'class_': TenantAwareSession})
login_manager = LoginManager()
login_manager.login_view = 'auth.giris'
login_manager.login_message = 'Bu sayfaya erişmek için giriş yapmanız gerekiyor.'
login_manager.login_message_category = 'warning'
migrate = Migrate()
csrf = CSRFProtect()
