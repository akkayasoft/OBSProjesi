from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.ders_dagitimi import Ders, OgretmenDersAtama
from app.models.muhasebe import Personel
from app.models.kayit import Sinif, Sube
from app.ders_dagitimi.forms import OgretmenDersAtamaForm

bp = Blueprint('atama', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    arama = request.args.get('arama', '')
    donem = request.args.get('donem', '2025-2026')
    page = request.args.get('page', 1, type=int)

    query = OgretmenDersAtama.query.filter_by(donem=donem)

    if arama:
        query = query.join(Personel, OgretmenDersAtama.ogretmen_id == Personel.id).filter(
            db.or_(
                Personel.ad.ilike(f'%{arama}%'),
                Personel.soyad.ilike(f'%{arama}%'),
            )
        )

    atamalar = query.order_by(OgretmenDersAtama.created_at.desc()).paginate(page=page, per_page=20)

    return render_template('ders_dagitimi/atama_listesi.html',
                           atamalar=atamalar,
                           arama=arama,
                           donem=donem)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = OgretmenDersAtamaForm()

    form.ogretmen_id.choices = [(p.id, f'{p.tam_ad} ({p.sicil_no})') for p in Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()]
    form.ders_id.choices = [(d.id, f'{d.kod} - {d.ad}') for d in Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()]
    form.sube_id.choices = [(s.id, s.tam_ad) for s in Sube.query.join(Sube.sinif).filter(Sube.aktif == True).order_by(Sinif.seviye, Sube.ad).all()]

    if form.validate_on_submit():
        # Aynı atama var mı kontrolü
        mevcut = OgretmenDersAtama.query.filter_by(
            ogretmen_id=form.ogretmen_id.data,
            ders_id=form.ders_id.data,
            sube_id=form.sube_id.data,
            donem=form.donem.data,
        ).first()
        if mevcut:
            flash('Bu öğretmen-ders-şube ataması zaten mevcut!', 'danger')
            return render_template('ders_dagitimi/atama_form.html',
                                   form=form, baslik='Yeni Öğretmen Ataması')

        atama = OgretmenDersAtama(
            ogretmen_id=form.ogretmen_id.data,
            ders_id=form.ders_id.data,
            sube_id=form.sube_id.data,
            donem=form.donem.data,
        )
        db.session.add(atama)
        db.session.commit()
        flash('Öğretmen ataması başarıyla eklendi.', 'success')
        return redirect(url_for('ders_dagitimi.atama.liste'))

    return render_template('ders_dagitimi/atama_form.html',
                           form=form, baslik='Yeni Öğretmen Ataması')


@bp.route('/<int:atama_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(atama_id):
    atama = OgretmenDersAtama.query.get_or_404(atama_id)
    db.session.delete(atama)
    db.session.commit()
    flash('Öğretmen ataması silindi.', 'success')
    return redirect(url_for('ders_dagitimi.atama.liste'))
