from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.user import User
from app.kullanici.forms import KullaniciForm, KullaniciDuzenleForm

bp = Blueprint('yonetim', __name__)


@bp.route('/liste')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    rol_filtre = request.args.get('rol', '')
    durum_filtre = request.args.get('durum', '')
    arama = request.args.get('arama', '')

    query = User.query

    if rol_filtre:
        query = query.filter(User.rol == rol_filtre)

    if durum_filtre == 'aktif':
        query = query.filter(User.aktif == True)  # noqa: E712
    elif durum_filtre == 'pasif':
        query = query.filter(User.aktif == False)  # noqa: E712

    if arama:
        arama_pattern = f'%{arama}%'
        query = query.filter(
            db.or_(
                User.username.ilike(arama_pattern),
                User.ad.ilike(arama_pattern),
                User.soyad.ilike(arama_pattern),
                User.email.ilike(arama_pattern),
            )
        )

    kullanicilar = query.order_by(User.olusturma_tarihi.desc()).paginate(
        page=page, per_page=20
    )

    return render_template('kullanici/liste.html',
                           kullanicilar=kullanicilar,
                           rol_filtre=rol_filtre,
                           durum_filtre=durum_filtre,
                           arama=arama)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = KullaniciForm()

    if form.validate_on_submit():
        kullanici = User(
            username=form.username.data,
            email=form.email.data,
            ad=form.ad.data,
            soyad=form.soyad.data,
            rol=form.rol.data,
            aktif=form.aktif.data,
        )
        kullanici.set_password(form.password.data)
        db.session.add(kullanici)
        db.session.commit()
        flash('Kullanici basariyla olusturuldu.', 'success')
        return redirect(url_for('kullanici.yonetim.liste'))

    return render_template('kullanici/yeni.html', form=form)


@bp.route('/<int:kullanici_id>')
@login_required
@role_required('admin')
def detay(kullanici_id):
    kullanici = User.query.get_or_404(kullanici_id)
    return render_template('kullanici/detay.html', kullanici=kullanici)


@bp.route('/<int:kullanici_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(kullanici_id):
    kullanici = User.query.get_or_404(kullanici_id)
    form = KullaniciDuzenleForm(kullanici_id=kullanici.id, obj=kullanici)

    if form.validate_on_submit():
        kullanici.username = form.username.data
        kullanici.email = form.email.data
        kullanici.ad = form.ad.data
        kullanici.soyad = form.soyad.data
        kullanici.rol = form.rol.data
        kullanici.aktif = form.aktif.data
        if form.password.data:
            kullanici.set_password(form.password.data)
        db.session.commit()
        flash('Kullanici basariyla guncellendi.', 'success')
        return redirect(url_for('kullanici.yonetim.detay', kullanici_id=kullanici.id))

    return render_template('kullanici/duzenle.html', form=form, kullanici=kullanici)


@bp.route('/<int:kullanici_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(kullanici_id):
    kullanici = User.query.get_or_404(kullanici_id)

    from flask_login import current_user
    if kullanici.id == current_user.id:
        flash('Kendi hesabinizi silemezsiniz.', 'danger')
        return redirect(url_for('kullanici.yonetim.liste'))

    db.session.delete(kullanici)
    db.session.commit()
    flash('Kullanici basariyla silindi.', 'success')
    return redirect(url_for('kullanici.yonetim.liste'))


@bp.route('/<int:kullanici_id>/sifre-sifirla', methods=['POST'])
@login_required
@role_required('admin')
def sifre_sifirla(kullanici_id):
    kullanici = User.query.get_or_404(kullanici_id)
    kullanici.set_password('obs123')
    db.session.commit()
    flash(f'{kullanici.tam_ad} kullanicisinin sifresi "obs123" olarak sifirlandi.', 'success')
    return redirect(url_for('kullanici.yonetim.detay', kullanici_id=kullanici.id))


@bp.route('/<int:kullanici_id>/aktif-toggle', methods=['POST'])
@login_required
@role_required('admin')
def aktif_toggle(kullanici_id):
    kullanici = User.query.get_or_404(kullanici_id)

    from flask_login import current_user
    if kullanici.id == current_user.id:
        flash('Kendi hesabinizi deaktif edemezsiniz.', 'danger')
        return redirect(url_for('kullanici.yonetim.liste'))

    kullanici.aktif = not kullanici.aktif
    db.session.commit()
    durum = 'aktif' if kullanici.aktif else 'pasif'
    flash(f'{kullanici.tam_ad} kullanicisi {durum} yapildi.', 'success')
    return redirect(url_for('kullanici.yonetim.liste'))
