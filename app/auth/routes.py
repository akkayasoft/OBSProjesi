from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.auth.forms import LoginForm
from app.models.user import User


@auth_bp.route('/giris', methods=['GET', 'POST'])
def giris():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

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
            return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Kullanıcı adı veya şifre hatalı.', 'danger')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/cikis')
@login_required
def cikis():
    logout_user()
    flash('Başarıyla çıkış yaptınız.', 'info')
    return redirect(url_for('auth.giris'))
