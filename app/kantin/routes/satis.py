from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.utils import role_required
from app.extensions import db
from app.models.kantin import KantinSatis, KantinUrun
from app.models.muhasebe import Ogrenci
from app.kantin.forms import KantinSatisForm

bp = Blueprint('satis', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    satislar = KantinSatis.query.order_by(
        KantinSatis.tarih.desc()
    ).paginate(page=page, per_page=20)
    return render_template('kantin/satis_listesi.html', satislar=satislar)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = KantinSatisForm()
    urunler = KantinUrun.query.filter_by(aktif=True).order_by(KantinUrun.ad).all()
    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    form.urun_id.choices = [(u.id, f'{u.ad} - {u.fiyat:.2f} TL') for u in urunler]
    form.ogrenci_id.choices = [(0, 'Misafir')] + [(o.id, f'{o.ogrenci_no} - {o.tam_ad}') for o in ogrenciler]

    if form.validate_on_submit():
        urun = KantinUrun.query.get(form.urun_id.data)
        if urun and urun.stok >= form.miktar.data:
            satis = KantinSatis(
                urun_id=form.urun_id.data,
                ogrenci_id=form.ogrenci_id.data if form.ogrenci_id.data != 0 else None,
                miktar=form.miktar.data,
                toplam_fiyat=urun.fiyat * form.miktar.data,
            )
            urun.stok -= form.miktar.data
            db.session.add(satis)
            db.session.commit()
            flash(f'Satis yapildi: {urun.ad} x{form.miktar.data} = {satis.toplam_fiyat:.2f} TL', 'success')
            return redirect(url_for('kantin.satis.yeni'))
        else:
            flash('Stok yetersiz!', 'danger')
    return render_template('kantin/satis.html', form=form)
