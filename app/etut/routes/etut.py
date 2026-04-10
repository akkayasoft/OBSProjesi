from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.etut import Etut, EtutKatilim
from app.models.muhasebe import Personel
from app.models.ders_dagitimi import Ders
from app.models.kayit import Sube
from app.etut.forms import EtutForm

bp = Blueprint('etut_yonetim', __name__)


def _populate_form_choices(form):
    """Form seceneklerini doldur."""
    form.ders_id.choices = [(0, '-- Ders Seciniz (Opsiyonel) --')] + [
        (d.id, f'{d.kod} - {d.ad}')
        for d in Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    ]
    form.ogretmen_id.choices = [
        (p.id, p.tam_ad)
        for p in Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    ]
    form.sube_id.choices = [(0, '-- Sube Seciniz (Opsiyonel) --')] + [
        (s.id, s.tam_ad)
        for s in Sube.query.filter_by(aktif=True).all()
    ]


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    gun = request.args.get('gun', '')
    donem = request.args.get('donem', '')
    arama = request.args.get('arama', '').strip()
    aktif_filtre = request.args.get('aktif', '')
    page = request.args.get('page', 1, type=int)

    query = Etut.query

    if gun:
        query = query.filter(Etut.gun == gun)
    if donem:
        query = query.filter(Etut.donem == donem)
    if arama:
        query = query.filter(
            db.or_(
                Etut.ad.ilike(f'%{arama}%'),
                Etut.derslik.ilike(f'%{arama}%')
            )
        )
    if aktif_filtre == '1':
        query = query.filter(Etut.aktif.is_(True))
    elif aktif_filtre == '0':
        query = query.filter(Etut.aktif.is_(False))

    etutler = query.order_by(
        Etut.gun, Etut.baslangic_saati
    ).paginate(page=page, per_page=20)

    # Mevcut donemleri al
    donemler = db.session.query(Etut.donem).distinct().order_by(Etut.donem.desc()).all()
    donemler = [d[0] for d in donemler]

    return render_template('etut/etut_listesi.html',
                           etutler=etutler,
                           gun=gun,
                           donem=donem,
                           arama=arama,
                           aktif_filtre=aktif_filtre,
                           donemler=donemler)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = EtutForm()
    _populate_form_choices(form)

    if form.validate_on_submit():
        etut = Etut(
            ad=form.ad.data,
            ders_id=form.ders_id.data if form.ders_id.data != 0 else None,
            ogretmen_id=form.ogretmen_id.data,
            sube_id=form.sube_id.data if form.sube_id.data != 0 else None,
            gun=form.gun.data,
            baslangic_saati=form.baslangic_saati.data,
            bitis_saati=form.bitis_saati.data,
            derslik=form.derslik.data,
            kontenjan=form.kontenjan.data,
            donem=form.donem.data,
            aktif=form.aktif.data,
            aciklama=form.aciklama.data,
        )
        db.session.add(etut)
        db.session.commit()
        flash('Etut basariyla olusturuldu.', 'success')
        return redirect(url_for('etut.etut_yonetim.liste'))

    return render_template('etut/etut_form.html',
                           form=form, baslik='Yeni Etut')


@bp.route('/<int:etut_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(etut_id):
    etut = Etut.query.get_or_404(etut_id)

    # Son katilim kayitlari
    son_katilimlar = EtutKatilim.query.filter_by(etut_id=etut.id).order_by(
        EtutKatilim.tarih.desc()
    ).limit(50).all()

    # Benzersiz ogrenciler
    ogrenci_ids = db.session.query(
        db.func.distinct(EtutKatilim.ogrenci_id)
    ).filter(EtutKatilim.etut_id == etut.id).all()
    ogrenci_ids = [o[0] for o in ogrenci_ids]

    return render_template('etut/etut_detay.html',
                           etut=etut,
                           son_katilimlar=son_katilimlar,
                           ogrenci_sayisi=len(ogrenci_ids))


@bp.route('/<int:etut_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(etut_id):
    etut = Etut.query.get_or_404(etut_id)
    form = EtutForm(obj=etut)
    _populate_form_choices(form)

    if form.validate_on_submit():
        etut.ad = form.ad.data
        etut.ders_id = form.ders_id.data if form.ders_id.data != 0 else None
        etut.ogretmen_id = form.ogretmen_id.data
        etut.sube_id = form.sube_id.data if form.sube_id.data != 0 else None
        etut.gun = form.gun.data
        etut.baslangic_saati = form.baslangic_saati.data
        etut.bitis_saati = form.bitis_saati.data
        etut.derslik = form.derslik.data
        etut.kontenjan = form.kontenjan.data
        etut.donem = form.donem.data
        etut.aktif = form.aktif.data
        etut.aciklama = form.aciklama.data

        db.session.commit()
        flash('Etut basariyla guncellendi.', 'success')
        return redirect(url_for('etut.etut_yonetim.detay', etut_id=etut.id))

    return render_template('etut/etut_form.html',
                           form=form, baslik='Etut Duzenle')


@bp.route('/<int:etut_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(etut_id):
    etut = Etut.query.get_or_404(etut_id)
    ad = etut.ad
    db.session.delete(etut)
    db.session.commit()
    flash(f'"{ad}" etudu silindi.', 'success')
    return redirect(url_for('etut.etut_yonetim.liste'))
