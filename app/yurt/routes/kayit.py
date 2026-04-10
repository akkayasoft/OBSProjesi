from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.yurt import YurtOda, YurtKayit
from app.models.muhasebe import Ogrenci
from app.yurt.forms import YurtKayitForm
from datetime import date

bp = Blueprint('kayit', __name__)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = YurtKayitForm()
    odalar = YurtOda.query.filter_by(durum='aktif').order_by(YurtOda.oda_no).all()
    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    form.oda_id.choices = [(o.id, f'{o.oda_no} ({o.bos_yatak}/{o.kapasite} bos)') for o in odalar]
    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}') for o in ogrenciler]

    if form.validate_on_submit():
        oda = YurtOda.query.get(form.oda_id.data)
        if oda and oda.bos_yatak <= 0:
            flash('Bu odada bos yatak yok.', 'danger')
            return render_template('yurt/kayit_form.html', form=form)

        kayit = YurtKayit(oda_id=form.oda_id.data, ogrenci_id=form.ogrenci_id.data,
                          yatak_no=form.yatak_no.data, baslangic_tarihi=form.baslangic_tarihi.data)
        db.session.add(kayit)
        db.session.commit()
        flash('Ogrenci odaya yerlestirildi.', 'success')
        return redirect(url_for('yurt.oda.detay', oda_id=form.oda_id.data))
    return render_template('yurt/kayit_form.html', form=form)


@bp.route('/<int:kayit_id>/cikar', methods=['POST'])
@login_required
@role_required('admin')
def cikar(kayit_id):
    kayit = YurtKayit.query.get_or_404(kayit_id)
    kayit.aktif = False
    kayit.bitis_tarihi = date.today()
    db.session.commit()
    flash('Ogrenci odadan cikarildi.', 'success')
    return redirect(url_for('yurt.oda.detay', oda_id=kayit.oda_id))
