from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.kayit import KayitDonemi
from app.kayit.forms import DonemForm

bp = Blueprint('donem', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def liste():
    donemler = KayitDonemi.query.order_by(KayitDonemi.baslangic_tarihi.desc()).all()
    return render_template('kayit/donem/liste.html', donemler=donemler)


@bp.route('/ekle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def ekle():
    form = DonemForm()
    if form.validate_on_submit():
        if form.bitis_tarihi.data <= form.baslangic_tarihi.data:
            flash('Bitiş tarihi başlangıç tarihinden sonra olmalıdır.', 'danger')
            return render_template('kayit/donem/donem_form.html',
                                   form=form, baslik='Yeni Dönem')

        donem = KayitDonemi(
            ad=form.ad.data,
            baslangic_tarihi=form.baslangic_tarihi.data,
            bitis_tarihi=form.bitis_tarihi.data,
            aciklama=form.aciklama.data
        )
        db.session.add(donem)
        db.session.commit()
        flash(f'"{form.ad.data}" dönemi başarıyla eklendi.', 'success')
        return redirect(url_for('kayit.donem.liste'))

    return render_template('kayit/donem/donem_form.html',
                           form=form, baslik='Yeni Dönem Ekle')


@bp.route('/<int:donem_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def duzenle(donem_id):
    donem = KayitDonemi.query.get_or_404(donem_id)
    form = DonemForm(obj=donem)
    if form.validate_on_submit():
        if form.bitis_tarihi.data <= form.baslangic_tarihi.data:
            flash('Bitiş tarihi başlangıç tarihinden sonra olmalıdır.', 'danger')
            return render_template('kayit/donem/donem_form.html',
                                   form=form, baslik='Dönem Düzenle')

        donem.ad = form.ad.data
        donem.baslangic_tarihi = form.baslangic_tarihi.data
        donem.bitis_tarihi = form.bitis_tarihi.data
        donem.aciklama = form.aciklama.data
        db.session.commit()
        flash(f'"{donem.ad}" dönemi güncellendi.', 'success')
        return redirect(url_for('kayit.donem.liste'))

    return render_template('kayit/donem/donem_form.html',
                           form=form, baslik='Dönem Düzenle')


@bp.route('/<int:donem_id>/durum', methods=['POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def durum_degistir(donem_id):
    donem = KayitDonemi.query.get_or_404(donem_id)
    donem.aktif = not donem.aktif
    db.session.commit()
    durum = 'aktif' if donem.aktif else 'pasif'
    flash(f'Dönem {durum} hale getirildi.', 'success')
    return redirect(url_for('kayit.donem.liste'))
