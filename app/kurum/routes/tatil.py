from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.kurum import Tatil, OgretimYili
from app.kurum.forms import TatilForm

bp = Blueprint('tatil', __name__)


@bp.route('/tatil/')
@login_required
@role_required('admin')
def liste():
    ogretim_yili_id = request.args.get('ogretim_yili_id', type=int)
    tur_filtre = request.args.get('tur', '')

    query = Tatil.query

    if ogretim_yili_id:
        query = query.filter(Tatil.ogretim_yili_id == ogretim_yili_id)

    if tur_filtre:
        query = query.filter(Tatil.tur == tur_filtre)

    tatiller = query.order_by(Tatil.baslangic_tarihi.asc()).all()
    ogretim_yillari = OgretimYili.query.order_by(
        OgretimYili.baslangic_tarihi.desc()
    ).all()

    return render_template('kurum/tatil_listesi.html',
                           tatiller=tatiller,
                           ogretim_yillari=ogretim_yillari,
                           ogretim_yili_id=ogretim_yili_id,
                           tur_filtre=tur_filtre)


@bp.route('/tatil/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = TatilForm()
    form.ogretim_yili_id.choices = [
        (oy.id, oy.ad) for oy in OgretimYili.query.order_by(
            OgretimYili.baslangic_tarihi.desc()
        ).all()
    ]

    if form.validate_on_submit():
        tatil = Tatil(
            ad=form.ad.data,
            baslangic_tarihi=form.baslangic_tarihi.data,
            bitis_tarihi=form.bitis_tarihi.data,
            tur=form.tur.data,
            ogretim_yili_id=form.ogretim_yili_id.data,
        )
        db.session.add(tatil)
        db.session.commit()
        flash('Tatil basariyla olusturuldu.', 'success')
        return redirect(url_for('kurum.tatil.liste'))

    return render_template('kurum/tatil_form.html', form=form, baslik='Yeni Tatil')


@bp.route('/tatil/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(id):
    tatil = Tatil.query.get_or_404(id)
    form = TatilForm(obj=tatil)
    form.ogretim_yili_id.choices = [
        (oy.id, oy.ad) for oy in OgretimYili.query.order_by(
            OgretimYili.baslangic_tarihi.desc()
        ).all()
    ]

    if form.validate_on_submit():
        form.populate_obj(tatil)
        db.session.commit()
        flash('Tatil basariyla guncellendi.', 'success')
        return redirect(url_for('kurum.tatil.liste'))

    return render_template('kurum/tatil_form.html', form=form,
                           baslik='Tatil Duzenle', tatil=tatil)


@bp.route('/tatil/<int:id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(id):
    tatil = Tatil.query.get_or_404(id)
    db.session.delete(tatil)
    db.session.commit()
    flash('Tatil basariyla silindi.', 'success')
    return redirect(url_for('kurum.tatil.liste'))
