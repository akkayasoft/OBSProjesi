from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from datetime import datetime
from app.extensions import db
from app.models.saglik import RevirKaydi
from app.models.muhasebe import Ogrenci
from app.saglik.forms import RevirKaydiForm

bp = Blueprint('revir', __name__)


@bp.route('/')
@login_required
@role_required('admin',)
def liste():
    arama = request.args.get('arama', '').strip()
    tarih_filtre = request.args.get('tarih', '').strip()
    page = request.args.get('page', 1, type=int)

    query = RevirKaydi.query.join(Ogrenci)

    if arama:
        query = query.filter(
            db.or_(
                Ogrenci.ad.ilike(f'%{arama}%'),
                Ogrenci.soyad.ilike(f'%{arama}%'),
                Ogrenci.ogrenci_no.ilike(f'%{arama}%'),
            )
        )
    if tarih_filtre:
        try:
            filtre_tarihi = datetime.strptime(tarih_filtre, '%Y-%m-%d').date()
            query = query.filter(db.func.date(RevirKaydi.tarih) == filtre_tarihi)
        except ValueError:
            pass

    kayitlar = query.order_by(RevirKaydi.tarih.desc()).paginate(page=page, per_page=20)

    return render_template('saglik/revir_listesi.html',
                           kayitlar=kayitlar,
                           arama=arama,
                           tarih_filtre=tarih_filtre)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin',)
def yeni():
    form = RevirKaydiForm()
    form.ogrenci_id.choices = [
        (o.id, f'{o.ogrenci_no} - {o.tam_ad}')
        for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()
    ]

    if form.validate_on_submit():
        kayit = RevirKaydi(
            ogrenci_id=form.ogrenci_id.data,
            tarih=form.tarih.data,
            sikayet=form.sikayet.data,
            yapilan_islem=form.yapilan_islem.data,
            verilen_ilac=form.verilen_ilac.data,
            sonuc=form.sonuc.data,
            ilgilenen_id=current_user.id,
        )
        db.session.add(kayit)
        db.session.commit()
        flash('Revir kaydı başarıyla oluşturuldu.', 'success')
        return redirect(url_for('saglik.revir.liste'))

    return render_template('saglik/revir_form.html',
                           form=form, baslik='Yeni Revir Kaydı')


@bp.route('/<int:kayit_id>')
@login_required
@role_required('admin',)
def detay(kayit_id):
    kayit = RevirKaydi.query.get_or_404(kayit_id)
    return render_template('saglik/revir_detay.html', kayit=kayit)
