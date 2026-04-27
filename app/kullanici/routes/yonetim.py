"""Kullanici Yonetimi route'lari.

Erisim politikasi:
- 'admin': tum kullanicilari (admin/yonetici dahil) yonetir.
- 'yonetici': sadece operasyonel rolleri (ogretmen, veli, ogrenci, muhasebeci)
  goruntuler/yonetir; admin ve yonetici hesaplarini goremez ve onlara
  ait endpoint'lerde 403 alir.

Bu sayede yonetici, dershane operasyonunu kontrol edebilir ama sistem
yetkililerine dokunamaz.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.utils import role_required
from app.extensions import db
from app.models.user import User
from app.kullanici.forms import KullaniciForm, KullaniciDuzenleForm

bp = Blueprint('yonetim', __name__)


# Yonetici'nin yonetebilecegi roller (admin ve yonetici DISARIDA)
YONETICI_ROLLERI = ('ogretmen', 'veli', 'ogrenci', 'muhasebeci')


def _kullanici_yonetebilir_mi(target_user: User) -> bool:
    """Mevcut kullanici target_user'i yonetebilir mi?

    - admin: her kullaniciyi yonetebilir
    - yonetici: sadece YONETICI_ROLLERI'ndekileri yonetebilir
    """
    if current_user.rol == 'admin':
        return True
    if current_user.rol == 'yonetici':
        return target_user.rol in YONETICI_ROLLERI
    return False


def _query_filtreli():
    """Mevcut kullanicinin gorebildigi User sorgusu."""
    if current_user.rol == 'admin':
        return User.query
    # yonetici
    return User.query.filter(User.rol.in_(YONETICI_ROLLERI))


@bp.route('/liste')
@login_required
@role_required('admin', 'yonetici')
def liste():
    page = request.args.get('page', 1, type=int)
    rol_filtre = request.args.get('rol', '')
    durum_filtre = request.args.get('durum', '')
    arama = request.args.get('arama', '')

    query = _query_filtreli()

    if rol_filtre:
        # Yoneticiler 'admin' veya 'yonetici' filtresi denerse iptal et
        if current_user.rol == 'yonetici' and rol_filtre not in YONETICI_ROLLERI:
            rol_filtre = ''
        else:
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

    # Form / liste UI'ina hangi rollerin secilebilecegini bildir
    if current_user.rol == 'admin':
        secilebilir_roller = (
            ('admin', 'Sistem Yöneticisi'),
            ('yonetici', 'Dershane Yöneticisi'),
            ('ogretmen', 'Öğretmen'),
            ('muhasebeci', 'Muhasebeci'),
            ('veli', 'Veli'),
            ('ogrenci', 'Öğrenci'),
        )
    else:
        secilebilir_roller = (
            ('ogretmen', 'Öğretmen'),
            ('muhasebeci', 'Muhasebeci'),
            ('veli', 'Veli'),
            ('ogrenci', 'Öğrenci'),
        )

    return render_template('kullanici/liste.html',
                           kullanicilar=kullanicilar,
                           rol_filtre=rol_filtre,
                           durum_filtre=durum_filtre,
                           arama=arama,
                           secilebilir_roller=secilebilir_roller)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'yonetici')
def yeni():
    form = KullaniciForm()

    # Yonetici icin rol secimini kisitla
    if current_user.rol == 'yonetici':
        form.rol.choices = [
            ('ogretmen', 'Ogretmen'),
            ('muhasebeci', 'Muhasebeci'),
            ('veli', 'Veli'),
            ('ogrenci', 'Ogrenci'),
        ]

    if form.validate_on_submit():
        # Tekrar kontrol — POST'tan gelen rol manipulasyonuna karsi
        if current_user.rol == 'yonetici' and form.rol.data not in YONETICI_ROLLERI:
            flash('Bu rolde kullanici olusturma yetkiniz yok.', 'danger')
            return redirect(url_for('kullanici.yonetim.liste'))

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
@role_required('admin', 'yonetici')
def detay(kullanici_id):
    kullanici = User.query.get_or_404(kullanici_id)
    if not _kullanici_yonetebilir_mi(kullanici):
        abort(403)
    return render_template('kullanici/detay.html', kullanici=kullanici)


@bp.route('/<int:kullanici_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'yonetici')
def duzenle(kullanici_id):
    kullanici = User.query.get_or_404(kullanici_id)
    if not _kullanici_yonetebilir_mi(kullanici):
        abort(403)

    form = KullaniciDuzenleForm(kullanici_id=kullanici.id, obj=kullanici)

    # Yonetici, hedef kullanicinin rolunu admin/yonetici'ye yukseltmesin
    if current_user.rol == 'yonetici':
        form.rol.choices = [
            ('ogretmen', 'Ogretmen'),
            ('muhasebeci', 'Muhasebeci'),
            ('veli', 'Veli'),
            ('ogrenci', 'Ogrenci'),
        ]

    if form.validate_on_submit():
        # POST'tan gelen rol guvenligi
        if current_user.rol == 'yonetici' and form.rol.data not in YONETICI_ROLLERI:
            flash('Bu role yukseltme yetkiniz yok.', 'danger')
            return redirect(url_for('kullanici.yonetim.liste'))

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
@role_required('admin', 'yonetici')
def sil(kullanici_id):
    kullanici = User.query.get_or_404(kullanici_id)
    if not _kullanici_yonetebilir_mi(kullanici):
        abort(403)

    if kullanici.id == current_user.id:
        flash('Kendi hesabinizi silemezsiniz.', 'danger')
        return redirect(url_for('kullanici.yonetim.liste'))

    db.session.delete(kullanici)
    db.session.commit()
    flash('Kullanici basariyla silindi.', 'success')
    return redirect(url_for('kullanici.yonetim.liste'))


@bp.route('/<int:kullanici_id>/sifre-sifirla', methods=['POST'])
@login_required
@role_required('admin', 'yonetici')
def sifre_sifirla(kullanici_id):
    kullanici = User.query.get_or_404(kullanici_id)
    if not _kullanici_yonetebilir_mi(kullanici):
        abort(403)
    kullanici.set_password('obs123')
    db.session.commit()
    flash(
        f'🔑 {kullanici.tam_ad} kullanicisinin sifresi sifirlandi. '
        f'Yeni sifre: obs123 — kullanicidan ilk girisinde degistirmesini '
        f'isteyiniz (bu mesaj kapatildiginda bir daha gosterilmez).',
        'sifre',
    )
    return redirect(url_for('kullanici.yonetim.detay', kullanici_id=kullanici.id))


@bp.route('/<int:kullanici_id>/aktif-toggle', methods=['POST'])
@login_required
@role_required('admin', 'yonetici')
def aktif_toggle(kullanici_id):
    kullanici = User.query.get_or_404(kullanici_id)
    if not _kullanici_yonetebilir_mi(kullanici):
        abort(403)

    if kullanici.id == current_user.id:
        flash('Kendi hesabinizi deaktif edemezsiniz.', 'danger')
        return redirect(url_for('kullanici.yonetim.liste'))

    kullanici.aktif = not kullanici.aktif
    db.session.commit()
    durum = 'aktif' if kullanici.aktif else 'pasif'
    flash(f'{kullanici.tam_ad} kullanicisi {durum} yapildi.', 'success')
    return redirect(url_for('kullanici.yonetim.liste'))
