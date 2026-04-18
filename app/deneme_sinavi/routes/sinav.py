"""Deneme sinavi CRUD."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.utils import role_required
from app.extensions import db
from app.models.deneme_sinavi import DenemeSinavi, DenemeDersi
from app.deneme_sinavi.forms import DenemeSinaviForm
from app.deneme_sinavi.sablonlar import varsayilan_dersler


bp = Blueprint('sinav', __name__, url_prefix='/sinav')


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    tip_filtre = request.args.get('tip', '')
    durum_filtre = request.args.get('durum', '')

    q = DenemeSinavi.query
    if tip_filtre:
        q = q.filter_by(sinav_tipi=tip_filtre)
    if durum_filtre:
        q = q.filter_by(durum=durum_filtre)

    sinavlar = q.order_by(DenemeSinavi.tarih.desc(), DenemeSinavi.id.desc()).all()
    return render_template('deneme_sinavi/liste.html',
                           sinavlar=sinavlar,
                           tip_filtre=tip_filtre,
                           durum_filtre=durum_filtre)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = DenemeSinaviForm()
    if form.validate_on_submit():
        sinav = DenemeSinavi(
            ad=form.ad.data,
            sinav_tipi=form.sinav_tipi.data,
            donem=form.donem.data,
            tarih=form.tarih.data,
            sure_dakika=form.sure_dakika.data,
            hedef_seviye=form.hedef_seviye.data or None,
            aciklama=form.aciklama.data or None,
            durum='hazirlaniyor',
            olusturan_id=current_user.id,
        )
        db.session.add(sinav)
        db.session.flush()

        # Sablondan ders bloklarini olustur
        if form.sablondan_olustur.data == 'evet':
            for d in varsayilan_dersler(form.sinav_tipi.data):
                db.session.add(DenemeDersi(
                    deneme_sinavi_id=sinav.id,
                    ders_kodu=d['ders_kodu'],
                    ders_adi=d['ders_adi'],
                    soru_sayisi=d['soru_sayisi'],
                    katsayi=d['katsayi'],
                    alan=d['alan'],
                    sira=d['sira'],
                ))

        db.session.commit()
        flash(f'Deneme sinavi olusturuldu: {sinav.ad}', 'success')
        return redirect(url_for('deneme_sinavi.sinav.detay', sinav_id=sinav.id))

    return render_template('deneme_sinavi/sinav_form.html', form=form, baslik='Yeni Deneme Sinavi')


@bp.route('/<int:sinav_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(sinav_id):
    sinav = DenemeSinavi.query.get_or_404(sinav_id)
    dersler = sinav.dersler.all()
    katilim_sayisi = sinav.katilimlar.count()
    return render_template('deneme_sinavi/detay.html',
                           sinav=sinav,
                           dersler=dersler,
                           katilim_sayisi=katilim_sayisi)


@bp.route('/<int:sinav_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(sinav_id):
    sinav = DenemeSinavi.query.get_or_404(sinav_id)
    form = DenemeSinaviForm(obj=sinav)
    # Duzenleme modunda sablondan olustur secenegi gizlenmeli
    if request.method == 'GET':
        form.sablondan_olustur.data = 'hayir'

    if form.validate_on_submit():
        sinav.ad = form.ad.data
        sinav.sinav_tipi = form.sinav_tipi.data
        sinav.donem = form.donem.data
        sinav.tarih = form.tarih.data
        sinav.sure_dakika = form.sure_dakika.data
        sinav.hedef_seviye = form.hedef_seviye.data or None
        sinav.aciklama = form.aciklama.data or None
        db.session.commit()
        flash('Deneme sinavi guncellendi.', 'success')
        return redirect(url_for('deneme_sinavi.sinav.detay', sinav_id=sinav.id))

    return render_template('deneme_sinavi/sinav_form.html',
                           form=form, sinav=sinav,
                           baslik=f'Duzenle: {sinav.ad}',
                           duzenleme=True)


@bp.route('/<int:sinav_id>/durum', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def durum_degistir(sinav_id):
    sinav = DenemeSinavi.query.get_or_404(sinav_id)
    yeni_durum = request.form.get('durum', '')
    valid = {'hazirlaniyor', 'yayinlandi', 'uygulandi', 'tamamlandi'}
    if yeni_durum not in valid:
        flash('Gecersiz durum.', 'danger')
    else:
        sinav.durum = yeni_durum
        db.session.commit()
        flash(f'Durum "{sinav.durum_str}" olarak guncellendi.', 'success')
    return redirect(url_for('deneme_sinavi.sinav.detay', sinav_id=sinav.id))


@bp.route('/<int:sinav_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(sinav_id):
    sinav = DenemeSinavi.query.get_or_404(sinav_id)
    ad = sinav.ad
    db.session.delete(sinav)
    db.session.commit()
    flash(f'"{ad}" silindi.', 'success')
    return redirect(url_for('deneme_sinavi.sinav.liste'))
