from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.servis import ServisKayit, Guzergah, ServisDurak
from app.models.muhasebe import Ogrenci
from app.servis.forms import ServisKayitForm

bp = Blueprint('kayit', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def liste():
    page = request.args.get('page', 1, type=int)
    durum = request.args.get('durum', '')

    query = ServisKayit.query

    if durum:
        query = query.filter(ServisKayit.durum == durum)

    kayitlar = query.order_by(
        ServisKayit.created_at.desc()
    ).paginate(page=page, per_page=20)

    return render_template('servis/kayit_listesi.html',
                           kayitlar=kayitlar, durum=durum)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni():
    form = ServisKayitForm()
    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    guzergahlar = Guzergah.query.filter_by(aktif=True).order_by(Guzergah.ad).all()
    duraklar = ServisDurak.query.order_by(ServisDurak.sira).all()

    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}') for o in ogrenciler]
    form.guzergah_id.choices = [(g.id, f'{g.kod} - {g.ad}') for g in guzergahlar]
    form.durak_id.choices = [(0, 'Seciniz')] + [(d.id, f'{d.guzergah.kod} - {d.ad}') for d in duraklar]

    if form.validate_on_submit():
        kayit = ServisKayit(
            ogrenci_id=form.ogrenci_id.data,
            guzergah_id=form.guzergah_id.data,
            durak_id=form.durak_id.data if form.durak_id.data != 0 else None,
            binis_yonu=form.binis_yonu.data,
            baslangic_tarihi=form.baslangic_tarihi.data,
            bitis_tarihi=form.bitis_tarihi.data,
            ucret=form.ucret.data,
            durum=form.durum.data,
        )
        db.session.add(kayit)
        db.session.commit()
        flash('Servis kaydi basariyla olusturuldu.', 'success')
        return redirect(url_for('servis.kayit.liste'))

    return render_template('servis/kayit_form.html',
                           form=form, baslik='Yeni Servis Kaydi')


@bp.route('/<int:kayit_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def duzenle(kayit_id):
    kayit = ServisKayit.query.get_or_404(kayit_id)
    form = ServisKayitForm(obj=kayit)

    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    guzergahlar = Guzergah.query.filter_by(aktif=True).order_by(Guzergah.ad).all()
    duraklar = ServisDurak.query.order_by(ServisDurak.sira).all()

    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}') for o in ogrenciler]
    form.guzergah_id.choices = [(g.id, f'{g.kod} - {g.ad}') for g in guzergahlar]
    form.durak_id.choices = [(0, 'Seciniz')] + [(d.id, f'{d.guzergah.kod} - {d.ad}') for d in duraklar]

    if form.validate_on_submit():
        kayit.ogrenci_id = form.ogrenci_id.data
        kayit.guzergah_id = form.guzergah_id.data
        kayit.durak_id = form.durak_id.data if form.durak_id.data != 0 else None
        kayit.binis_yonu = form.binis_yonu.data
        kayit.baslangic_tarihi = form.baslangic_tarihi.data
        kayit.bitis_tarihi = form.bitis_tarihi.data
        kayit.ucret = form.ucret.data
        kayit.durum = form.durum.data
        db.session.commit()
        flash('Servis kaydi basariyla guncellendi.', 'success')
        return redirect(url_for('servis.kayit.liste'))

    return render_template('servis/kayit_form.html',
                           form=form, baslik='Servis Kaydi Duzenle')


@bp.route('/<int:kayit_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(kayit_id):
    kayit = ServisKayit.query.get_or_404(kayit_id)
    db.session.delete(kayit)
    db.session.commit()
    flash('Servis kaydi basariyla silindi.', 'success')
    return redirect(url_for('servis.kayit.liste'))
