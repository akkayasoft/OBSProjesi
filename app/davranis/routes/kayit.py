from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.utils import role_required
from app.extensions import db
from app.models.davranis import DavranisDeğerlendirme, DavranisKurali
from app.models.muhasebe import Ogrenci, Personel
from app.models.kayit import Sinif
from app.davranis.forms import DavranisKaydiForm
from datetime import date

bp = Blueprint('kayit', __name__)


def _populate_form_choices(form):
    """Form seceneklerini doldur."""
    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}')
                                for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()]
    form.ogretmen_id.choices = [(p.id, f'{p.sicil_no} - {p.tam_ad}')
                                 for p in Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()]
    form.sinif_id.choices = [(0, '-- Sinif Seciniz --')] + [
        (s.id, s.ad) for s in Sinif.query.filter_by(aktif=True).order_by(Sinif.ad).all()
    ]
    kurallar = DavranisKurali.query.filter_by(aktif=True).order_by(DavranisKurali.ad).all()
    form.kural_id.choices = [(0, '-- Kural Seciniz (Istege Bagli) --')] + [
        (k.id, f'{k.ad} ({k.varsayilan_puan:+d})') for k in kurallar
    ]


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    tur = request.args.get('tur', '')
    kategori = request.args.get('kategori', '')
    sinif_id = request.args.get('sinif_id', '', type=str)
    ogrenci_id = request.args.get('ogrenci_id', '', type=str)
    baslangic = request.args.get('baslangic', '')
    bitis = request.args.get('bitis', '')
    page = request.args.get('page', 1, type=int)

    query = DavranisDeğerlendirme.query

    if tur:
        query = query.filter(DavranisDeğerlendirme.tur == tur)
    if kategori:
        query = query.filter(DavranisDeğerlendirme.kategori == kategori)
    if sinif_id:
        query = query.filter(DavranisDeğerlendirme.sinif_id == int(sinif_id))
    if ogrenci_id:
        query = query.filter(DavranisDeğerlendirme.ogrenci_id == int(ogrenci_id))
    if baslangic:
        try:
            from datetime import datetime
            b_tarih = datetime.strptime(baslangic, '%Y-%m-%d').date()
            query = query.filter(DavranisDeğerlendirme.tarih >= b_tarih)
        except ValueError:
            pass
    if bitis:
        try:
            from datetime import datetime
            bt_tarih = datetime.strptime(bitis, '%Y-%m-%d').date()
            query = query.filter(DavranisDeğerlendirme.tarih <= bt_tarih)
        except ValueError:
            pass

    kayitlar = query.order_by(
        DavranisDeğerlendirme.tarih.desc()
    ).paginate(page=page, per_page=20)

    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.ad).all()
    ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()

    return render_template('davranis/kayit_listesi.html',
                           kayitlar=kayitlar,
                           siniflar=siniflar,
                           ogrenciler=ogrenciler,
                           tur=tur,
                           kategori=kategori,
                           sinif_id=sinif_id,
                           ogrenci_id=ogrenci_id,
                           baslangic=baslangic,
                           bitis=bitis)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = DavranisKaydiForm()
    _populate_form_choices(form)

    if not form.tarih.data:
        form.tarih.data = date.today()

    if form.validate_on_submit():
        kayit = DavranisDeğerlendirme(
            ogrenci_id=form.ogrenci_id.data,
            ogretmen_id=form.ogretmen_id.data,
            sinif_id=form.sinif_id.data if form.sinif_id.data != 0 else None,
            kural_id=form.kural_id.data if form.kural_id.data != 0 else None,
            tur=form.tur.data,
            kategori=form.kategori.data,
            puan=form.puan.data,
            aciklama=form.aciklama.data,
            tarih=form.tarih.data,
        )
        db.session.add(kayit)
        db.session.commit()
        flash('Davranis degerlendirme kaydi basariyla olusturuldu.', 'success')
        return redirect(url_for('davranis.kayit.liste'))

    return render_template('davranis/kayit_form.html',
                           form=form, baslik='Yeni Davranis Kaydi')


@bp.route('/<int:kayit_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(kayit_id):
    kayit = DavranisDeğerlendirme.query.get_or_404(kayit_id)
    form = DavranisKaydiForm(obj=kayit)
    _populate_form_choices(form)

    if form.validate_on_submit():
        kayit.ogrenci_id = form.ogrenci_id.data
        kayit.ogretmen_id = form.ogretmen_id.data
        kayit.sinif_id = form.sinif_id.data if form.sinif_id.data != 0 else None
        kayit.kural_id = form.kural_id.data if form.kural_id.data != 0 else None
        kayit.tur = form.tur.data
        kayit.kategori = form.kategori.data
        kayit.puan = form.puan.data
        kayit.aciklama = form.aciklama.data
        kayit.tarih = form.tarih.data

        db.session.commit()
        flash('Davranis degerlendirme kaydi basariyla guncellendi.', 'success')
        return redirect(url_for('davranis.kayit.liste'))

    return render_template('davranis/kayit_form.html',
                           form=form, baslik='Davranis Kaydi Duzenle')


@bp.route('/<int:kayit_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(kayit_id):
    kayit = DavranisDeğerlendirme.query.get_or_404(kayit_id)
    db.session.delete(kayit)
    db.session.commit()
    flash('Davranis degerlendirme kaydi silindi.', 'success')
    return redirect(url_for('davranis.kayit.liste'))
