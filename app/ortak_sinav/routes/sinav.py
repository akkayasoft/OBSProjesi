from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.ortak_sinav import OrtakSinav
from app.models.ders_dagitimi import Ders
from app.ortak_sinav.forms import OrtakSinavForm
from datetime import date

bp = Blueprint('sinav', __name__)


def _populate_form_choices(form):
    """Form seceneklerini doldur."""
    form.ders_id.choices = [
        (d.id, f'{d.kod} - {d.ad}')
        for d in Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    ]


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    durum = request.args.get('durum', '')
    seviye = request.args.get('seviye', '', type=str)
    ders_id = request.args.get('ders_id', '', type=str)
    donem = request.args.get('donem', '')
    page = request.args.get('page', 1, type=int)

    query = OrtakSinav.query

    if durum:
        query = query.filter(OrtakSinav.durum == durum)
    if seviye:
        query = query.filter(OrtakSinav.seviye == int(seviye))
    if ders_id:
        query = query.filter(OrtakSinav.ders_id == int(ders_id))
    if donem:
        query = query.filter(OrtakSinav.donem == donem)

    sinavlar = query.order_by(OrtakSinav.tarih.desc()).paginate(page=page, per_page=20)

    dersler = Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()

    return render_template('ortak_sinav/sinav_listesi.html',
                           sinavlar=sinavlar,
                           dersler=dersler,
                           durum=durum,
                           seviye=seviye,
                           ders_id=ders_id,
                           donem=donem)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = OrtakSinavForm()
    _populate_form_choices(form)

    if not form.tarih.data:
        form.tarih.data = date.today()

    if form.validate_on_submit():
        sinav = OrtakSinav(
            ad=form.ad.data,
            ders_id=form.ders_id.data,
            seviye=form.seviye.data,
            donem=form.donem.data,
            tarih=form.tarih.data,
            sure_dakika=form.sure_dakika.data,
            soru_sayisi=form.soru_sayisi.data,
            toplam_puan=form.toplam_puan.data,
            durum=form.durum.data,
            aciklama=form.aciklama.data,
        )
        db.session.add(sinav)
        db.session.commit()
        flash('Ortak sinav basariyla olusturuldu.', 'success')
        return redirect(url_for('ortak_sinav.sinav.liste'))

    return render_template('ortak_sinav/sinav_form.html',
                           form=form, baslik='Yeni Ortak Sinav')


@bp.route('/<int:sinav_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(sinav_id):
    sinav = OrtakSinav.query.get_or_404(sinav_id)
    sonuclar = sinav.sonuclar.order_by(db.text('puan DESC')).all()

    return render_template('ortak_sinav/sinav_detay.html',
                           sinav=sinav, sonuclar=sonuclar)


@bp.route('/<int:sinav_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(sinav_id):
    sinav = OrtakSinav.query.get_or_404(sinav_id)
    form = OrtakSinavForm(obj=sinav)
    _populate_form_choices(form)

    if form.validate_on_submit():
        sinav.ad = form.ad.data
        sinav.ders_id = form.ders_id.data
        sinav.seviye = form.seviye.data
        sinav.donem = form.donem.data
        sinav.tarih = form.tarih.data
        sinav.sure_dakika = form.sure_dakika.data
        sinav.soru_sayisi = form.soru_sayisi.data
        sinav.toplam_puan = form.toplam_puan.data
        sinav.durum = form.durum.data
        sinav.aciklama = form.aciklama.data

        db.session.commit()
        flash('Ortak sinav basariyla guncellendi.', 'success')
        return redirect(url_for('ortak_sinav.sinav.detay', sinav_id=sinav.id))

    return render_template('ortak_sinav/sinav_form.html',
                           form=form, baslik='Sinav Duzenle')


@bp.route('/<int:sinav_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(sinav_id):
    sinav = OrtakSinav.query.get_or_404(sinav_id)
    db.session.delete(sinav)
    db.session.commit()
    flash('Ortak sinav silindi.', 'success')
    return redirect(url_for('ortak_sinav.sinav.liste'))
