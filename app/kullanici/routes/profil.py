from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.extensions import db
from app.kullanici.forms import ProfilForm, SifreDegistirForm

bp = Blueprint('profil', __name__)


@bp.route('/profil')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def profil():
    return render_template('kullanici/profil.html', kullanici=current_user)


@bp.route('/profil/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def profil_duzenle():
    form = ProfilForm(kullanici_id=current_user.id, obj=current_user)

    if form.validate_on_submit():
        current_user.ad = form.ad.data
        current_user.soyad = form.soyad.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Profiliniz basariyla guncellendi.', 'success')
        return redirect(url_for('kullanici.profil.profil'))

    return render_template('kullanici/profil_duzenle.html', form=form)


@bp.route('/profil/sifre', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def sifre_degistir():
    form = SifreDegistirForm()

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash('Mevcut sifreniz yanlis.', 'danger')
            return render_template('kullanici/sifre_degistir.html', form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Sifreniz basariyla degistirildi.', 'success')
        return redirect(url_for('kullanici.profil.profil'))

    return render_template('kullanici/sifre_degistir.html', form=form)
