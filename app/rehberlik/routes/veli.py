from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.rehberlik import VeliGorusmesi
from app.models.muhasebe import Ogrenci
from app.rehberlik.forms import VeliGorusmesiForm

bp = Blueprint('veli', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    tur = request.args.get('tur', '')
    arama = request.args.get('arama', '').strip()
    page = request.args.get('page', 1, type=int)

    query = VeliGorusmesi.query

    if tur:
        query = query.filter(VeliGorusmesi.gorusme_turu == tur)
    if arama:
        query = query.filter(
            db.or_(
                VeliGorusmesi.konu.ilike(f'%{arama}%'),
                VeliGorusmesi.veli_adi.ilike(f'%{arama}%')
            )
        )

    gorusmeler = query.order_by(
        VeliGorusmesi.gorusme_tarihi.desc()
    ).paginate(page=page, per_page=20)

    return render_template('rehberlik/veli_listesi.html',
                           gorusmeler=gorusmeler,
                           tur=tur,
                           arama=arama)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = VeliGorusmesiForm()
    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}')
                                for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()]

    if form.validate_on_submit():
        gorusme = VeliGorusmesi(
            ogrenci_id=form.ogrenci_id.data,
            veli_adi=form.veli_adi.data,
            veli_telefon=form.veli_telefon.data,
            gorusme_tarihi=form.gorusme_tarihi.data,
            gorusme_turu=form.gorusme_turu.data,
            konu=form.konu.data,
            icerik=form.icerik.data,
            sonuc=form.sonuc.data,
            gorusen_id=current_user.id,
        )
        db.session.add(gorusme)
        db.session.commit()
        flash('Veli gorusmesi basariyla olusturuldu.', 'success')
        return redirect(url_for('rehberlik.veli.liste'))

    return render_template('rehberlik/veli_form.html',
                           form=form, baslik='Yeni Veli Gorusmesi')


@bp.route('/<int:gorusme_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(gorusme_id):
    gorusme = VeliGorusmesi.query.get_or_404(gorusme_id)
    form = VeliGorusmesiForm(obj=gorusme)
    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}')
                                for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()]

    if form.validate_on_submit():
        gorusme.ogrenci_id = form.ogrenci_id.data
        gorusme.veli_adi = form.veli_adi.data
        gorusme.veli_telefon = form.veli_telefon.data
        gorusme.gorusme_tarihi = form.gorusme_tarihi.data
        gorusme.gorusme_turu = form.gorusme_turu.data
        gorusme.konu = form.konu.data
        gorusme.icerik = form.icerik.data
        gorusme.sonuc = form.sonuc.data

        db.session.commit()
        flash('Veli gorusmesi basariyla guncellendi.', 'success')
        return redirect(url_for('rehberlik.veli.liste'))

    return render_template('rehberlik/veli_form.html',
                           form=form, baslik='Veli Gorusmesi Duzenle')


@bp.route('/<int:gorusme_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(gorusme_id):
    gorusme = VeliGorusmesi.query.get_or_404(gorusme_id)
    konu = gorusme.konu
    db.session.delete(gorusme)
    db.session.commit()
    flash(f'"{konu}" veli gorusmesi silindi.', 'success')
    return redirect(url_for('rehberlik.veli.liste'))
