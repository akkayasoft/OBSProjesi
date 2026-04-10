from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.kutuphane import Kitap, KitapOdunc
from app.models.muhasebe import Ogrenci, Personel
from app.kutuphane.forms import OduncForm
from datetime import date

bp = Blueprint('odunc', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    durum = request.args.get('durum', '')
    query = KitapOdunc.query
    if durum:
        query = query.filter(KitapOdunc.durum == durum)
    kayitlar = query.order_by(KitapOdunc.odunc_tarihi.desc()).paginate(page=page, per_page=20)
    return render_template('kutuphane/odunc_listesi.html', kayitlar=kayitlar, durum=durum)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = OduncForm()
    kitaplar = Kitap.query.filter(Kitap.mevcut_adet > 0).order_by(Kitap.baslik).all()
    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    personeller = Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()

    form.kitap_id.choices = [(k.id, f'{k.baslik} - {k.yazar} ({k.mevcut_adet} adet)') for k in kitaplar]
    form.ogrenci_id.choices = [(0, 'Seciniz')] + [(o.id, f'{o.ogrenci_no} - {o.tam_ad}') for o in ogrenciler]
    form.personel_id.choices = [(0, 'Seciniz')] + [(p.id, f'{p.ad} {p.soyad}') for p in personeller]

    if form.validate_on_submit():
        kitap = Kitap.query.get(form.kitap_id.data)
        if not kitap or kitap.mevcut_adet <= 0:
            flash('Kitap musait degil.', 'danger')
            return redirect(url_for('kutuphane.odunc.yeni'))

        odunc = KitapOdunc(
            kitap_id=form.kitap_id.data,
            son_iade_tarihi=form.son_iade_tarihi.data,
            aciklama=form.aciklama.data,
        )
        if form.kisi_turu.data == 'ogrenci' and form.ogrenci_id.data:
            odunc.ogrenci_id = form.ogrenci_id.data
        elif form.kisi_turu.data == 'personel' and form.personel_id.data:
            odunc.personel_id = form.personel_id.data
        else:
            flash('Lutfen bir kisi secin.', 'warning')
            return render_template('kutuphane/odunc_form.html', form=form)

        kitap.mevcut_adet -= 1
        db.session.add(odunc)
        db.session.commit()
        flash(f'"{kitap.baslik}" odunc verildi.', 'success')
        return redirect(url_for('kutuphane.odunc.liste'))
    return render_template('kutuphane/odunc_form.html', form=form)


@bp.route('/<int:odunc_id>/iade', methods=['POST'])
@login_required
@role_required('admin')
def iade(odunc_id):
    odunc = KitapOdunc.query.get_or_404(odunc_id)
    if odunc.durum != 'odunc':
        flash('Bu kitap zaten iade edilmis.', 'warning')
        return redirect(url_for('kutuphane.odunc.liste'))

    odunc.durum = 'iade_edildi'
    odunc.iade_tarihi = date.today()
    odunc.kitap.mevcut_adet += 1
    db.session.commit()
    flash(f'"{odunc.kitap.baslik}" iade alindi.', 'success')
    return redirect(url_for('kutuphane.odunc.liste'))
