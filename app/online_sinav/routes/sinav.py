from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.online_sinav import OnlineSinav
from app.models.ders_dagitimi import Ders
from app.models.kayit import Sube, Sinif
from app.online_sinav.forms import OnlineSinavForm

bp = Blueprint('sinav', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    ders_id = request.args.get('ders_id', '', type=str)
    durum = request.args.get('durum', '')
    arama = request.args.get('arama', '').strip()
    page = request.args.get('page', 1, type=int)

    query = OnlineSinav.query

    if ders_id:
        query = query.filter(OnlineSinav.ders_id == int(ders_id))
    if arama:
        query = query.filter(OnlineSinav.baslik.ilike(f'%{arama}%'))

    sinavlar = query.order_by(OnlineSinav.created_at.desc()).paginate(page=page, per_page=20)

    # Durum filtresi Python tarafinda (property-based)
    dersler = Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()

    return render_template('online_sinav/sinav_listesi.html',
                           sinavlar=sinavlar,
                           dersler=dersler,
                           ders_id=ders_id,
                           durum=durum,
                           arama=arama)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = OnlineSinavForm()
    dersler = Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    subeler = Sube.query.join(Sinif).filter(Sube.aktif == True).order_by(Sinif.seviye, Sube.ad).all()

    form.ders_id.choices = [(0, '-- Ders Seçiniz --')] + [(d.id, f'{d.kod} - {d.ad}') for d in dersler]
    form.sube_id.choices = [(0, 'Tüm Şubeler')] + [(s.id, s.tam_ad) for s in subeler]

    if form.validate_on_submit():
        sinav = OnlineSinav(
            baslik=form.baslik.data,
            aciklama=form.aciklama.data,
            ders_id=form.ders_id.data,
            sube_id=form.sube_id.data if form.sube_id.data != 0 else None,
            olusturan_id=current_user.id,
            sure=form.sure.data,
            baslangic_zamani=form.baslangic_zamani.data,
            bitis_zamani=form.bitis_zamani.data,
            sinav_turu=form.sinav_turu.data,
            zorluk=form.zorluk.data,
            toplam_puan=form.toplam_puan.data,
            gecme_puani=form.gecme_puani.data,
            sorulari_karistir=form.sorulari_karistir.data,
            secenekleri_karistir=form.secenekleri_karistir.data,
            sonuclari_goster=form.sonuclari_goster.data,
        )
        db.session.add(sinav)
        db.session.commit()
        flash('Sınav başarıyla oluşturuldu.', 'success')
        return redirect(url_for('online_sinav.sinav.detay', sinav_id=sinav.id))

    return render_template('online_sinav/sinav_form.html', form=form, baslik='Yeni Sınav')


@bp.route('/<int:sinav_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(sinav_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)
    return render_template('online_sinav/sinav_detay.html', sinav=sinav)


@bp.route('/<int:sinav_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(sinav_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)
    form = OnlineSinavForm(obj=sinav)
    dersler = Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    subeler = Sube.query.join(Sinif).filter(Sube.aktif == True).order_by(Sinif.seviye, Sube.ad).all()

    form.ders_id.choices = [(0, '-- Ders Seçiniz --')] + [(d.id, f'{d.kod} - {d.ad}') for d in dersler]
    form.sube_id.choices = [(0, 'Tüm Şubeler')] + [(s.id, s.tam_ad) for s in subeler]

    if form.validate_on_submit():
        sinav.baslik = form.baslik.data
        sinav.aciklama = form.aciklama.data
        sinav.ders_id = form.ders_id.data
        sinav.sube_id = form.sube_id.data if form.sube_id.data != 0 else None
        sinav.sure = form.sure.data
        sinav.baslangic_zamani = form.baslangic_zamani.data
        sinav.bitis_zamani = form.bitis_zamani.data
        sinav.sinav_turu = form.sinav_turu.data
        sinav.zorluk = form.zorluk.data
        sinav.toplam_puan = form.toplam_puan.data
        sinav.gecme_puani = form.gecme_puani.data
        sinav.sorulari_karistir = form.sorulari_karistir.data
        sinav.secenekleri_karistir = form.secenekleri_karistir.data
        sinav.sonuclari_goster = form.sonuclari_goster.data
        db.session.commit()
        flash('Sınav başarıyla güncellendi.', 'success')
        return redirect(url_for('online_sinav.sinav.detay', sinav_id=sinav.id))

    if request.method == 'GET':
        form.sube_id.data = sinav.sube_id or 0

    return render_template('online_sinav/sinav_form.html', form=form, sinav=sinav, baslik='Sınavı Düzenle')


@bp.route('/<int:sinav_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(sinav_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)
    db.session.delete(sinav)
    db.session.commit()
    flash('Sınav başarıyla silindi.', 'success')
    return redirect(url_for('online_sinav.sinav.liste'))


@bp.route('/<int:sinav_id>/aktif-toggle', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def aktif_toggle(sinav_id):
    sinav = OnlineSinav.query.get_or_404(sinav_id)
    sinav.aktif = not sinav.aktif
    db.session.commit()
    durum = 'aktifleştirildi' if sinav.aktif else 'pasifleştirildi'
    flash(f'Sınav {durum}.', 'success')
    return redirect(url_for('online_sinav.sinav.detay', sinav_id=sinav.id))
