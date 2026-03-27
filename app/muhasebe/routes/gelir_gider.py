from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models.muhasebe import GelirGiderKaydi, GelirGiderKategorisi, BankaHesabi
from app.muhasebe.forms import GelirGiderForm, KategoriForm
from app.muhasebe.utils import banka_hareketi_olustur

bp = Blueprint('gelir_gider', __name__)


@bp.route('/')
@login_required
def liste():
    page = request.args.get('page', 1, type=int)
    tur_filtre = request.args.get('tur', '')
    kategori_filtre = request.args.get('kategori', 0, type=int)

    query = GelirGiderKaydi.query

    if tur_filtre:
        query = query.filter_by(tur=tur_filtre)
    if kategori_filtre:
        query = query.filter_by(kategori_id=kategori_filtre)

    kayitlar = query.order_by(GelirGiderKaydi.tarih.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    kategoriler = GelirGiderKategorisi.query.filter_by(aktif=True).all()

    return render_template('muhasebe/gelir_gider/liste.html',
                           kayitlar=kayitlar,
                           kategoriler=kategoriler,
                           tur_filtre=tur_filtre,
                           kategori_filtre=kategori_filtre)


@bp.route('/ekle', methods=['GET', 'POST'])
@login_required
def ekle():
    form = GelirGiderForm()

    kategoriler = GelirGiderKategorisi.query.filter_by(aktif=True).all()
    form.kategori_id.choices = [(k.id, f'{k.ad} ({k.tur})') for k in kategoriler]

    hesaplar = BankaHesabi.query.filter_by(aktif=True).all()
    form.banka_hesap_id.choices = [(0, '-- Seçiniz (Opsiyonel) --')] + \
        [(h.id, f'{h.banka_adi} - {h.hesap_adi}') for h in hesaplar]

    if form.validate_on_submit():
        kayit = GelirGiderKaydi(
            kategori_id=form.kategori_id.data,
            tur=form.tur.data,
            tutar=form.tutar.data,
            aciklama=form.aciklama.data,
            tarih=form.tarih.data,
            belge_no=form.belge_no.data,
            banka_hesap_id=form.banka_hesap_id.data if form.banka_hesap_id.data else None,
            olusturan_id=current_user.id
        )
        db.session.add(kayit)

        # Banka hesabı seçildiyse hareket oluştur
        if form.banka_hesap_id.data:
            tur = 'giris' if form.tur.data == 'gelir' else 'cikis'
            banka_hareketi_olustur(
                form.banka_hesap_id.data, tur, form.tutar.data,
                aciklama=f'{form.tur.data.title()}: {form.aciklama.data or ""}'
            )

        db.session.commit()
        flash(f'{form.tur.data.title()} kaydı başarıyla eklendi.', 'success')
        return redirect(url_for('muhasebe.gelir_gider.liste'))

    return render_template('muhasebe/gelir_gider/ekle.html', form=form, baslik='Yeni Kayıt Ekle')


@bp.route('/<int:id>/duzenle', methods=['GET', 'POST'])
@login_required
def duzenle(id):
    kayit = GelirGiderKaydi.query.get_or_404(id)
    form = GelirGiderForm(obj=kayit)

    kategoriler = GelirGiderKategorisi.query.filter_by(aktif=True).all()
    form.kategori_id.choices = [(k.id, f'{k.ad} ({k.tur})') for k in kategoriler]

    hesaplar = BankaHesabi.query.filter_by(aktif=True).all()
    form.banka_hesap_id.choices = [(0, '-- Seçiniz (Opsiyonel) --')] + \
        [(h.id, f'{h.banka_adi} - {h.hesap_adi}') for h in hesaplar]

    if form.validate_on_submit():
        kayit.kategori_id = form.kategori_id.data
        kayit.tur = form.tur.data
        kayit.tutar = form.tutar.data
        kayit.aciklama = form.aciklama.data
        kayit.tarih = form.tarih.data
        kayit.belge_no = form.belge_no.data
        kayit.banka_hesap_id = form.banka_hesap_id.data if form.banka_hesap_id.data else None

        db.session.commit()
        flash('Kayıt başarıyla güncellendi.', 'success')
        return redirect(url_for('muhasebe.gelir_gider.liste'))

    return render_template('muhasebe/gelir_gider/ekle.html', form=form, baslik='Kaydı Düzenle')


@bp.route('/<int:id>/sil', methods=['POST'])
@login_required
def sil(id):
    kayit = GelirGiderKaydi.query.get_or_404(id)
    db.session.delete(kayit)
    db.session.commit()
    flash('Kayıt başarıyla silindi.', 'success')
    return redirect(url_for('muhasebe.gelir_gider.liste'))


@bp.route('/kategoriler', methods=['GET', 'POST'])
@login_required
def kategoriler():
    form = KategoriForm()

    if form.validate_on_submit():
        kategori = GelirGiderKategorisi(
            ad=form.ad.data,
            tur=form.tur.data
        )
        db.session.add(kategori)
        db.session.commit()
        flash('Kategori başarıyla eklendi.', 'success')
        return redirect(url_for('muhasebe.gelir_gider.kategoriler'))

    kategoriler = GelirGiderKategorisi.query.order_by(GelirGiderKategorisi.tur, GelirGiderKategorisi.ad).all()
    return render_template('muhasebe/gelir_gider/kategoriler.html', form=form, kategoriler=kategoriler)


@bp.route('/kategoriler/<int:id>/sil', methods=['POST'])
@login_required
def kategori_sil(id):
    kategori = GelirGiderKategorisi.query.get_or_404(id)
    if kategori.kayitlar.count() > 0:
        flash('Bu kategoriye ait kayıtlar var. Önce kayıtları silin.', 'danger')
    else:
        db.session.delete(kategori)
        db.session.commit()
        flash('Kategori başarıyla silindi.', 'success')
    return redirect(url_for('muhasebe.gelir_gider.kategoriler'))
