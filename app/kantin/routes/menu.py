from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.kantin import YemekMenu
from app.kantin.forms import YemekMenuForm
from datetime import date, timedelta

bp = Blueprint('menu', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    menuler = YemekMenu.query.order_by(YemekMenu.tarih.desc()).paginate(page=page, per_page=20)
    return render_template('kantin/menu_listesi.html', menuler=menuler)


@bp.route('/haftalik')
@login_required
@role_required('admin')
def haftalik():
    bugun = date.today()
    hafta_basi = bugun - timedelta(days=bugun.weekday())
    hafta_sonu = hafta_basi + timedelta(days=4)
    menuler = YemekMenu.query.filter(
        YemekMenu.tarih >= hafta_basi, YemekMenu.tarih <= hafta_sonu
    ).order_by(YemekMenu.tarih).all()
    return render_template('kantin/haftalik_menu.html', menuler=menuler,
                           hafta_basi=hafta_basi, hafta_sonu=hafta_sonu)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = YemekMenuForm()
    if form.validate_on_submit():
        menu = YemekMenu(tarih=form.tarih.data, gun=form.gun.data,
                         kahvalti=form.kahvalti.data, ogle_yemegi=form.ogle_yemegi.data,
                         ara_ogun=form.ara_ogun.data, kalori=form.kalori.data,
                         aciklama=form.aciklama.data)
        db.session.add(menu)
        db.session.commit()
        flash('Menu eklendi.', 'success')
        return redirect(url_for('kantin.menu.liste'))
    return render_template('kantin/menu_form.html', form=form, baslik='Yeni Menu')


@bp.route('/<int:menu_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(menu_id):
    menu = YemekMenu.query.get_or_404(menu_id)
    form = YemekMenuForm(obj=menu)
    if form.validate_on_submit():
        menu.tarih = form.tarih.data
        menu.gun = form.gun.data
        menu.kahvalti = form.kahvalti.data
        menu.ogle_yemegi = form.ogle_yemegi.data
        menu.ara_ogun = form.ara_ogun.data
        menu.kalori = form.kalori.data
        menu.aciklama = form.aciklama.data
        db.session.commit()
        flash('Menu guncellendi.', 'success')
        return redirect(url_for('kantin.menu.liste'))
    return render_template('kantin/menu_form.html', form=form, baslik='Menu Duzenle')


@bp.route('/<int:menu_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(menu_id):
    menu = YemekMenu.query.get_or_404(menu_id)
    db.session.delete(menu)
    db.session.commit()
    flash('Menu silindi.', 'success')
    return redirect(url_for('kantin.menu.liste'))
