from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.saglik import AsiTakip
from app.models.muhasebe import Ogrenci
from app.saglik.forms import AsiTakipForm

bp = Blueprint('asi', __name__)


@bp.route('/')
@login_required
@role_required('admin',)
def liste():
    arama = request.args.get('arama', '').strip()
    durum_filtre = request.args.get('durum', '').strip()
    page = request.args.get('page', 1, type=int)

    query = AsiTakip.query.join(Ogrenci)

    if arama:
        query = query.filter(
            db.or_(
                Ogrenci.ad.ilike(f'%{arama}%'),
                Ogrenci.soyad.ilike(f'%{arama}%'),
                AsiTakip.asi_adi.ilike(f'%{arama}%'),
            )
        )
    if durum_filtre:
        query = query.filter(AsiTakip.durum == durum_filtre)

    kayitlar = query.order_by(AsiTakip.asi_tarihi.desc()).paginate(page=page, per_page=20)

    return render_template('saglik/asi_listesi.html',
                           kayitlar=kayitlar,
                           arama=arama,
                           durum_filtre=durum_filtre)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin',)
def yeni():
    form = AsiTakipForm()
    form.ogrenci_id.choices = [
        (o.id, f'{o.ogrenci_no} - {o.tam_ad}')
        for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    ]

    if form.validate_on_submit():
        kayit = AsiTakip(
            ogrenci_id=form.ogrenci_id.data,
            asi_adi=form.asi_adi.data,
            asi_tarihi=form.asi_tarihi.data,
            hatirlatma_tarihi=form.hatirlatma_tarihi.data,
            durum=form.durum.data,
            aciklama=form.aciklama.data,
        )
        db.session.add(kayit)
        db.session.commit()
        flash('Aşı kaydı başarıyla oluşturuldu.', 'success')
        return redirect(url_for('saglik.asi.liste'))

    return render_template('saglik/asi_form.html',
                           form=form, baslik='Yeni Aşı Kaydı')


@bp.route('/<int:kayit_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin',)
def duzenle(kayit_id):
    kayit = AsiTakip.query.get_or_404(kayit_id)
    form = AsiTakipForm(obj=kayit)
    form.ogrenci_id.choices = [
        (o.id, f'{o.ogrenci_no} - {o.tam_ad}')
        for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    ]

    if form.validate_on_submit():
        kayit.ogrenci_id = form.ogrenci_id.data
        kayit.asi_adi = form.asi_adi.data
        kayit.asi_tarihi = form.asi_tarihi.data
        kayit.hatirlatma_tarihi = form.hatirlatma_tarihi.data
        kayit.durum = form.durum.data
        kayit.aciklama = form.aciklama.data

        db.session.commit()
        flash('Aşı kaydı başarıyla güncellendi.', 'success')
        return redirect(url_for('saglik.asi.liste'))

    return render_template('saglik/asi_form.html',
                           form=form, baslik='Aşı Kaydı Düzenle')


@bp.route('/<int:kayit_id>/sil', methods=['POST'])
@login_required
@role_required('admin',)
def sil(kayit_id):
    kayit = AsiTakip.query.get_or_404(kayit_id)
    asi_adi = kayit.asi_adi
    db.session.delete(kayit)
    db.session.commit()
    flash(f'"{asi_adi}" aşı kaydı silindi.', 'success')
    return redirect(url_for('saglik.asi.liste'))
