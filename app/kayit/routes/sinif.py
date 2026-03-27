from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.extensions import db
from app.models.kayit import Sinif, Sube
from app.kayit.forms import SinifForm, SubeForm

bp = Blueprint('sinif', __name__)


@bp.route('/')
@login_required
def liste():
    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.seviye).all()
    return render_template('kayit/sinif/liste.html', siniflar=siniflar)


@bp.route('/ekle', methods=['GET', 'POST'])
@login_required
def sinif_ekle():
    form = SinifForm()
    if form.validate_on_submit():
        sinif = Sinif(ad=form.ad.data, seviye=form.seviye.data)
        db.session.add(sinif)
        db.session.commit()
        flash(f'"{form.ad.data}" başarıyla eklendi.', 'success')
        return redirect(url_for('kayit.sinif.liste'))

    return render_template('kayit/sinif/sinif_form.html',
                           form=form, baslik='Yeni Sınıf Ekle')


@bp.route('/<int:sinif_id>/sil', methods=['POST'])
@login_required
def sinif_sil(sinif_id):
    sinif = Sinif.query.get_or_404(sinif_id)
    if sinif.ogrenci_sayisi > 0:
        flash('Bu sınıfta öğrenci bulunduğu için silinemez.', 'danger')
    else:
        sinif.aktif = False
        db.session.commit()
        flash('Sınıf başarıyla silindi.', 'success')
    return redirect(url_for('kayit.sinif.liste'))


@bp.route('/sube-ekle', methods=['GET', 'POST'])
@login_required
def sube_ekle():
    form = SubeForm()
    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.seviye).all()
    form.sinif_id.choices = [(s.id, s.ad) for s in siniflar]

    if form.validate_on_submit():
        sube = Sube(
            sinif_id=form.sinif_id.data,
            ad=form.ad.data,
            kontenjan=form.kontenjan.data
        )
        db.session.add(sube)
        db.session.commit()
        flash(f'Şube başarıyla eklendi.', 'success')
        return redirect(url_for('kayit.sinif.liste'))

    return render_template('kayit/sinif/sube_form.html',
                           form=form, baslik='Yeni Şube Ekle')


@bp.route('/sube/<int:sube_id>/sil', methods=['POST'])
@login_required
def sube_sil(sube_id):
    sube = Sube.query.get_or_404(sube_id)
    if sube.aktif_ogrenci_sayisi > 0:
        flash('Bu şubede öğrenci bulunduğu için silinemez.', 'danger')
    else:
        sube.aktif = False
        db.session.commit()
        flash('Şube başarıyla silindi.', 'success')
    return redirect(url_for('kayit.sinif.liste'))
