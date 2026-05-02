from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urljoin, urlsplit
from app.auth import auth_bp
from app.auth.forms import LoginForm
from app.models.user import User


def _is_safe_next_url(target):
    if not target:
        return False
    ref_url = urlsplit(request.host_url)
    test_url = urlsplit(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


def _giris_sonrasi_hedef(user):
    """Role gore giris sonrasi yonlendirilecek URL'i dondur."""
    if user.rol in ('ogrenci', 'veli'):
        return url_for('ogrenci_portal.dashboard.index')
    # Surucu kursu tenant'i ise OBS dashboard yerine kendi anasayfasi
    from flask import g
    tenant = getattr(g, 'tenant', None)
    if tenant is not None and getattr(tenant, 'kurum_tipi', None) == 'surucu_kursu':
        return url_for('surucu_kursu.dashboard')
    return url_for('main.dashboard')


@auth_bp.route('/giris', methods=['GET', 'POST'])
def giris():
    if current_user.is_authenticated:
        return redirect(_giris_sonrasi_hedef(current_user))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if not user.aktif:
                flash('Hesabınız devre dışı bırakılmış.', 'danger')
                return redirect(url_for('auth.giris'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            flash(f'Hoş geldiniz, {user.tam_ad}!', 'success')
            if _is_safe_next_url(next_page):
                return redirect(next_page)
            return redirect(_giris_sonrasi_hedef(user))
        else:
            flash('Kullanıcı adı veya şifre hatalı.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/cikis')
@login_required
def cikis():
    logout_user()
    flash('Başarıyla çıkış yaptınız.', 'info')
    return redirect(url_for('auth.giris'))


@auth_bp.route('/impersonate')
def impersonate_consume():
    """Sistem panelinden gelen kisa omurlu token'i tuketir, hedef
    kullaniciyi bu tenant'ta login eder.

    Token /sistem/tenant/<id>/impersonate uretiyor ve sadece bu tenant
    icin gecerlidir; max 2 dakika ve TEK KULLANIMLIK (master DB'de
    jti uzerinden atomic UPDATE ile track edilir).
    """
    from datetime import datetime
    from flask import current_app, g
    from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
    from sqlalchemy import update
    from app.tenancy.master import master_session
    from app.tenancy.models import ImpersonationToken

    token = request.args.get('t', '')
    if not token:
        flash('Geçersiz impersonate isteği.', 'danger')
        return redirect(url_for('auth.giris'))

    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'],
                                salt='sistem-impersonate-v1')
    try:
        data = s.loads(token, max_age=120)
    except SignatureExpired:
        flash('Impersonate bağlantısı süresi doldu (2dk). '
              'Sistem panelden tekrar deneyin.', 'warning')
        return redirect(url_for('auth.giris'))
    except BadSignature:
        flash('Geçersiz impersonate imzası.', 'danger')
        return redirect(url_for('auth.giris'))

    jti = data.get('jti')
    if not jti:
        # Eski format token (jti'siz) — guvenlik nedeniyle reddet
        flash('Geçersiz token formatı. Lütfen sistem panelden yeniden '
              'impersonate başlatın.', 'danger')
        return redirect(url_for('auth.giris'))

    # Mevcut tenant'i kontrol et — token sadece kendi tenant'inda gecerli
    tenant_obj = getattr(g, 'tenant', None)
    beklenen_slug = data.get('tenant_slug')
    if tenant_obj is not None and beklenen_slug and tenant_obj.slug != beklenen_slug:
        flash('Token bu tenant icin geçerli değil.', 'danger')
        return redirect(url_for('auth.giris'))

    # Atomic mark-used: jti var ve kullanildi_mi=False ise True'ya cevir.
    # rowcount 0 ise ya zaten kullanilmis ya da hic kayit yok -> reddet.
    try:
        with master_session() as ms:
            result = ms.execute(
                update(ImpersonationToken)
                .where(
                    ImpersonationToken.jti == jti,
                    ImpersonationToken.kullanildi_mi.is_(False),
                )
                .values(
                    kullanildi_mi=True,
                    kullanim_zamani=datetime.utcnow(),
                    kullanim_ip=request.remote_addr,
                )
            )
            ms.commit()
            if result.rowcount == 0:
                flash('Bu impersonate bağlantısı daha önce kullanıldı veya '
                      'iptal edilmiş. Sistem panelden yenisini başlatın.', 'danger')
                return redirect(url_for('auth.giris'))
    except Exception as e:
        flash(f'Impersonate doğrulanamadı: {type(e).__name__}', 'danger')
        return redirect(url_for('auth.giris'))

    user = User.query.filter_by(id=data.get('user_id'), aktif=True).first()
    if not user:
        flash('Hedef kullanıcı bulunamadı veya pasif.', 'danger')
        return redirect(url_for('auth.giris'))

    if current_user.is_authenticated:
        logout_user()
    login_user(user, remember=False)
    flash(f'Sistem yöneticisi olarak "{user.tam_ad}" hesabıyla '
          f'giriş yapıldı (impersonate).', 'info')
    return redirect(_giris_sonrasi_hedef(user))
