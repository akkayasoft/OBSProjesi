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
