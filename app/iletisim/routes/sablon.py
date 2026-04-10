from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.iletisim import MesajSablonu
from app.iletisim.forms import MesajSablonuForm

bp = Blueprint('sablon', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def liste():
    sablonlar = MesajSablonu.query.filter_by(aktif=True).order_by(
        MesajSablonu.kategori, MesajSablonu.baslik
    ).all()
    return render_template('iletisim/sablon_listesi.html', sablonlar=sablonlar)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def yeni():
    form = MesajSablonuForm()

    if form.validate_on_submit():
        sablon = MesajSablonu(
            baslik=form.baslik.data,
            icerik=form.icerik.data,
            kategori=form.kategori.data,
            olusturan_id=current_user.id,
        )
        db.session.add(sablon)
        db.session.commit()
        flash('Şablon başarıyla oluşturuldu.', 'success')
        return redirect(url_for('iletisim.sablon.liste'))

    return render_template('iletisim/sablon_form.html', form=form, baslik='Yeni Şablon')


@bp.route('/<int:sablon_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def duzenle(sablon_id):
    sablon = MesajSablonu.query.get_or_404(sablon_id)
    form = MesajSablonuForm(obj=sablon)

    if form.validate_on_submit():
        sablon.baslik = form.baslik.data
        sablon.icerik = form.icerik.data
        sablon.kategori = form.kategori.data
        db.session.commit()
        flash('Şablon başarıyla güncellendi.', 'success')
        return redirect(url_for('iletisim.sablon.liste'))

    return render_template('iletisim/sablon_form.html', form=form, baslik='Şablon Düzenle')


@bp.route('/<int:sablon_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def sil(sablon_id):
    sablon = MesajSablonu.query.get_or_404(sablon_id)
    sablon.aktif = False
    db.session.commit()
    flash('Şablon silindi.', 'success')
    return redirect(url_for('iletisim.sablon.liste'))


@bp.route('/<int:sablon_id>/json')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def json_getir(sablon_id):
    sablon = MesajSablonu.query.get_or_404(sablon_id)
    return jsonify({
        'baslik': sablon.baslik,
        'icerik': sablon.icerik,
        'kategori': sablon.kategori,
    })
