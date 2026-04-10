from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.kurum import OgretimYili
from app.kurum.forms import OgretimYiliForm

bp = Blueprint('ogretim_yili', __name__)


@bp.route('/ogretim-yili/')
@login_required
@role_required('admin')
def liste():
    ogretim_yillari = OgretimYili.query.order_by(
        OgretimYili.baslangic_tarihi.desc()
    ).all()
    return render_template('kurum/ogretim_yili_listesi.html',
                           ogretim_yillari=ogretim_yillari)


@bp.route('/ogretim-yili/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = OgretimYiliForm()

    if form.validate_on_submit():
        ogretim_yili = OgretimYili(
            ad=form.ad.data,
            baslangic_tarihi=form.baslangic_tarihi.data,
            bitis_tarihi=form.bitis_tarihi.data,
            yariyil_baslangic=form.yariyil_baslangic.data,
            yariyil_bitis=form.yariyil_bitis.data,
            aktif=form.aktif.data,
        )
        db.session.add(ogretim_yili)
        db.session.commit()
        flash('Ogretim yili basariyla olusturuldu.', 'success')
        return redirect(url_for('kurum.ogretim_yili.liste'))

    return render_template('kurum/ogretim_yili_form.html', form=form, baslik='Yeni Ogretim Yili')


@bp.route('/ogretim-yili/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(id):
    ogretim_yili = OgretimYili.query.get_or_404(id)
    form = OgretimYiliForm(obj=ogretim_yili)

    if form.validate_on_submit():
        form.populate_obj(ogretim_yili)
        db.session.commit()
        flash('Ogretim yili basariyla guncellendi.', 'success')
        return redirect(url_for('kurum.ogretim_yili.liste'))

    return render_template('kurum/ogretim_yili_form.html', form=form,
                           baslik='Ogretim Yili Duzenle', ogretim_yili=ogretim_yili)


@bp.route('/ogretim-yili/<int:id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(id):
    ogretim_yili = OgretimYili.query.get_or_404(id)
    db.session.delete(ogretim_yili)
    db.session.commit()
    flash('Ogretim yili basariyla silindi.', 'success')
    return redirect(url_for('kurum.ogretim_yili.liste'))
