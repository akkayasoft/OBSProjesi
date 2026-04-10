from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.yurt import YurtOda
from app.yurt.forms import YurtOdaForm

bp = Blueprint('oda', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    durum = request.args.get('durum', '')
    query = YurtOda.query
    if durum:
        query = query.filter(YurtOda.durum == durum)
    odalar = query.order_by(YurtOda.oda_no).paginate(page=page, per_page=20)
    return render_template('yurt/oda_listesi.html', odalar=odalar, durum=durum)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = YurtOdaForm()
    if form.validate_on_submit():
        oda = YurtOda(oda_no=form.oda_no.data, bina=form.bina.data, kat=form.kat.data,
                      kapasite=form.kapasite.data, cinsiyet=form.cinsiyet.data,
                      durum=form.durum.data, aciklama=form.aciklama.data)
        db.session.add(oda)
        db.session.commit()
        flash('Oda eklendi.', 'success')
        return redirect(url_for('yurt.oda.liste'))
    return render_template('yurt/oda_form.html', form=form, baslik='Yeni Oda')


@bp.route('/<int:oda_id>')
@login_required
@role_required('admin')
def detay(oda_id):
    oda = YurtOda.query.get_or_404(oda_id)
    kayitlar = oda.kayitlar.filter_by(aktif=True).all()
    return render_template('yurt/oda_detay.html', oda=oda, kayitlar=kayitlar)


@bp.route('/<int:oda_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(oda_id):
    oda = YurtOda.query.get_or_404(oda_id)
    form = YurtOdaForm(obj=oda)
    if form.validate_on_submit():
        oda.oda_no = form.oda_no.data
        oda.bina = form.bina.data
        oda.kat = form.kat.data
        oda.kapasite = form.kapasite.data
        oda.cinsiyet = form.cinsiyet.data
        oda.durum = form.durum.data
        oda.aciklama = form.aciklama.data
        db.session.commit()
        flash('Oda guncellendi.', 'success')
        return redirect(url_for('yurt.oda.detay', oda_id=oda.id))
    return render_template('yurt/oda_form.html', form=form, baslik='Oda Duzenle')


@bp.route('/<int:oda_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(oda_id):
    oda = YurtOda.query.get_or_404(oda_id)
    db.session.delete(oda)
    db.session.commit()
    flash('Oda silindi.', 'success')
    return redirect(url_for('yurt.oda.liste'))
