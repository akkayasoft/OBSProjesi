from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.servis import Guzergah, ServisDurak, Arac, ServisKayit
from app.servis.forms import GuzergahForm

bp = Blueprint('guzergah', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    guzergahlar = Guzergah.query.filter_by(aktif=True).order_by(
        Guzergah.kod
    ).paginate(page=page, per_page=12)

    return render_template('servis/guzergah_listesi.html',
                           guzergahlar=guzergahlar)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = GuzergahForm()

    if form.validate_on_submit():
        guzergah = Guzergah(
            ad=form.ad.data,
            kod=form.kod.data,
            aciklama=form.aciklama.data,
            baslangic_noktasi=form.baslangic_noktasi.data,
            bitis_noktasi=form.bitis_noktasi.data,
            mesafe_km=form.mesafe_km.data,
            tahmini_sure=form.tahmini_sure.data,
            aktif=form.aktif.data,
        )
        db.session.add(guzergah)
        db.session.commit()
        flash('Guzergah basariyla olusturuldu.', 'success')
        return redirect(url_for('servis.guzergah.liste'))

    return render_template('servis/guzergah_form.html',
                           form=form, baslik='Yeni Guzergah')


@bp.route('/<int:guzergah_id>')
@login_required
@role_required('admin')
def detay(guzergah_id):
    guzergah = Guzergah.query.get_or_404(guzergah_id)
    duraklar = ServisDurak.query.filter_by(
        guzergah_id=guzergah.id
    ).order_by(ServisDurak.sira).all()

    arac = Arac.query.filter_by(
        guzergah_id=guzergah.id, aktif=True
    ).first()

    kayitlar = ServisKayit.query.filter_by(
        guzergah_id=guzergah.id, durum='aktif'
    ).all()

    return render_template('servis/guzergah_detay.html',
                           guzergah=guzergah, duraklar=duraklar,
                           arac=arac, kayitlar=kayitlar)


@bp.route('/<int:guzergah_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(guzergah_id):
    guzergah = Guzergah.query.get_or_404(guzergah_id)
    form = GuzergahForm(obj=guzergah)

    if form.validate_on_submit():
        guzergah.ad = form.ad.data
        guzergah.kod = form.kod.data
        guzergah.aciklama = form.aciklama.data
        guzergah.baslangic_noktasi = form.baslangic_noktasi.data
        guzergah.bitis_noktasi = form.bitis_noktasi.data
        guzergah.mesafe_km = form.mesafe_km.data
        guzergah.tahmini_sure = form.tahmini_sure.data
        guzergah.aktif = form.aktif.data
        db.session.commit()
        flash('Guzergah basariyla guncellendi.', 'success')
        return redirect(url_for('servis.guzergah.detay', guzergah_id=guzergah.id))

    return render_template('servis/guzergah_form.html',
                           form=form, baslik='Guzergah Duzenle')


@bp.route('/<int:guzergah_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(guzergah_id):
    guzergah = Guzergah.query.get_or_404(guzergah_id)
    db.session.delete(guzergah)
    db.session.commit()
    flash('Guzergah basariyla silindi.', 'success')
    return redirect(url_for('servis.guzergah.liste'))
