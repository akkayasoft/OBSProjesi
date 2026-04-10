from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.kurum import Derslik
from app.kurum.forms import DerslikForm

bp = Blueprint('derslik', __name__)


@bp.route('/derslik/')
@login_required
@role_required('admin')
def liste():
    tur_filtre = request.args.get('tur', '')
    durum_filtre = request.args.get('durum', '')

    query = Derslik.query

    if tur_filtre:
        query = query.filter(Derslik.tur == tur_filtre)

    if durum_filtre == 'aktif':
        query = query.filter(Derslik.aktif == True)  # noqa: E712
    elif durum_filtre == 'pasif':
        query = query.filter(Derslik.aktif == False)  # noqa: E712

    derslikler = query.order_by(Derslik.ad.asc()).all()

    # Istatistikler
    toplam_kapasite = sum(d.kapasite or 0 for d in derslikler if d.aktif)

    return render_template('kurum/derslik_listesi.html',
                           derslikler=derslikler,
                           tur_filtre=tur_filtre,
                           durum_filtre=durum_filtre,
                           toplam_kapasite=toplam_kapasite)


@bp.route('/derslik/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = DerslikForm()

    if form.validate_on_submit():
        derslik = Derslik(
            ad=form.ad.data,
            kat=form.kat.data,
            kapasite=form.kapasite.data,
            tur=form.tur.data,
            donanim=form.donanim.data,
            aktif=form.aktif.data,
        )
        db.session.add(derslik)
        db.session.commit()
        flash('Derslik basariyla olusturuldu.', 'success')
        return redirect(url_for('kurum.derslik.liste'))

    return render_template('kurum/derslik_form.html', form=form, baslik='Yeni Derslik')


@bp.route('/derslik/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(id):
    derslik = Derslik.query.get_or_404(id)
    form = DerslikForm(obj=derslik)

    if form.validate_on_submit():
        form.populate_obj(derslik)
        db.session.commit()
        flash('Derslik basariyla guncellendi.', 'success')
        return redirect(url_for('kurum.derslik.liste'))

    return render_template('kurum/derslik_form.html', form=form,
                           baslik='Derslik Duzenle', derslik=derslik)


@bp.route('/derslik/<int:id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(id):
    derslik = Derslik.query.get_or_404(id)
    db.session.delete(derslik)
    db.session.commit()
    flash('Derslik basariyla silindi.', 'success')
    return redirect(url_for('kurum.derslik.liste'))
