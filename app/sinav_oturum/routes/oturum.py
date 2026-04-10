from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.utils import role_required
from app.extensions import db
from app.models.sinav_oturum import SinavOturum
from app.models.muhasebe import Personel
from app.models.kayit import Sinif
from app.models.ders_dagitimi import Ders
from app.sinav_oturum.forms import SinavOturumForm
from datetime import date

bp = Blueprint('oturum', __name__)


def _populate_form_choices(form):
    """Form seceneklerini doldur."""
    form.sinif_id.choices = [(s.id, s.ad)
                             for s in Sinif.query.filter_by(aktif=True).order_by(Sinif.ad).all()]
    form.ders_id.choices = [(d.id, f'{d.kod} - {d.ad}')
                            for d in Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()]
    form.ogretmen_id.choices = [(p.id, f'{p.sicil_no} - {p.tam_ad}')
                                for p in Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()]


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    sinav_turu = request.args.get('sinav_turu', '')
    durum = request.args.get('durum', '')
    sinif_id = request.args.get('sinif_id', '', type=str)
    ders_id = request.args.get('ders_id', '', type=str)
    baslangic = request.args.get('baslangic', '')
    bitis = request.args.get('bitis', '')
    page = request.args.get('page', 1, type=int)

    query = SinavOturum.query

    if sinav_turu:
        query = query.filter(SinavOturum.sinav_turu == sinav_turu)
    if durum:
        query = query.filter(SinavOturum.durum == durum)
    if sinif_id:
        query = query.filter(SinavOturum.sinif_id == int(sinif_id))
    if ders_id:
        query = query.filter(SinavOturum.ders_id == int(ders_id))
    if baslangic:
        try:
            from datetime import datetime
            b_tarih = datetime.strptime(baslangic, '%Y-%m-%d').date()
            query = query.filter(SinavOturum.tarih >= b_tarih)
        except ValueError:
            pass
    if bitis:
        try:
            from datetime import datetime
            bt_tarih = datetime.strptime(bitis, '%Y-%m-%d').date()
            query = query.filter(SinavOturum.tarih <= bt_tarih)
        except ValueError:
            pass

    oturumlar = query.order_by(
        SinavOturum.tarih.desc(), SinavOturum.baslangic_saati.desc()
    ).paginate(page=page, per_page=20)

    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.ad).all()
    dersler = Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()

    return render_template('sinav_oturum/oturum_listesi.html',
                           oturumlar=oturumlar,
                           siniflar=siniflar,
                           dersler=dersler,
                           sinav_turu=sinav_turu,
                           durum=durum,
                           sinif_id=sinif_id,
                           ders_id=ders_id,
                           baslangic=baslangic,
                           bitis=bitis)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = SinavOturumForm()
    _populate_form_choices(form)

    if not form.tarih.data:
        form.tarih.data = date.today()

    if form.validate_on_submit():
        oturum = SinavOturum(
            ad=form.ad.data,
            sinav_turu=form.sinav_turu.data,
            tarih=form.tarih.data,
            baslangic_saati=form.baslangic_saati.data,
            bitis_saati=form.bitis_saati.data,
            sinif_id=form.sinif_id.data,
            ders_id=form.ders_id.data,
            ogretmen_id=form.ogretmen_id.data,
            derslik=form.derslik.data or None,
            durum=form.durum.data,
            aciklama=form.aciklama.data or None,
        )
        db.session.add(oturum)
        db.session.commit()
        flash('Sinav oturumu basariyla olusturuldu.', 'success')
        return redirect(url_for('sinav_oturum.oturum.liste'))

    return render_template('sinav_oturum/oturum_form.html',
                           form=form, baslik='Yeni Sinav Oturumu')


@bp.route('/<int:oturum_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(oturum_id):
    oturum = SinavOturum.query.get_or_404(oturum_id)
    return render_template('sinav_oturum/oturum_detay.html', oturum=oturum)


@bp.route('/<int:oturum_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(oturum_id):
    oturum = SinavOturum.query.get_or_404(oturum_id)
    form = SinavOturumForm(obj=oturum)
    _populate_form_choices(form)

    if form.validate_on_submit():
        oturum.ad = form.ad.data
        oturum.sinav_turu = form.sinav_turu.data
        oturum.tarih = form.tarih.data
        oturum.baslangic_saati = form.baslangic_saati.data
        oturum.bitis_saati = form.bitis_saati.data
        oturum.sinif_id = form.sinif_id.data
        oturum.ders_id = form.ders_id.data
        oturum.ogretmen_id = form.ogretmen_id.data
        oturum.derslik = form.derslik.data or None
        oturum.durum = form.durum.data
        oturum.aciklama = form.aciklama.data or None

        db.session.commit()
        flash('Sinav oturumu basariyla guncellendi.', 'success')
        return redirect(url_for('sinav_oturum.oturum.detay', oturum_id=oturum.id))

    return render_template('sinav_oturum/oturum_form.html',
                           form=form, baslik='Sinav Oturumu Duzenle')


@bp.route('/<int:oturum_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(oturum_id):
    oturum = SinavOturum.query.get_or_404(oturum_id)
    db.session.delete(oturum)
    db.session.commit()
    flash('Sinav oturumu silindi.', 'success')
    return redirect(url_for('sinav_oturum.oturum.liste'))


@bp.route('/<int:oturum_id>/durum-degistir', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def durum_degistir(oturum_id):
    oturum = SinavOturum.query.get_or_404(oturum_id)
    yeni_durum = request.form.get('durum')
    gecerli_durumlar = ['planlanmis', 'devam_ediyor', 'tamamlandi', 'iptal']
    if yeni_durum not in gecerli_durumlar:
        flash('Gecersiz durum.', 'danger')
        return redirect(url_for('sinav_oturum.oturum.detay', oturum_id=oturum.id))

    oturum.durum = yeni_durum
    db.session.commit()
    flash(f'Sinav oturumu durumu "{oturum.durum_str}" olarak guncellendi.', 'success')
    return redirect(url_for('sinav_oturum.oturum.detay', oturum_id=oturum.id))
