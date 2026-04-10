from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.rehberlik import RehberlikPlani
from app.models.muhasebe import Ogrenci
from app.rehberlik.forms import RehberlikPlaniForm

bp = Blueprint('plan', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    durum = request.args.get('durum', '')
    arama = request.args.get('arama', '').strip()
    page = request.args.get('page', 1, type=int)

    query = RehberlikPlani.query

    if durum:
        query = query.filter(RehberlikPlani.durum == durum)
    if arama:
        query = query.filter(
            db.or_(
                RehberlikPlani.baslik.ilike(f'%{arama}%'),
                RehberlikPlani.hedefler.ilike(f'%{arama}%')
            )
        )

    planlar = query.order_by(
        RehberlikPlani.baslangic_tarihi.desc()
    ).paginate(page=page, per_page=20)

    return render_template('rehberlik/plan_listesi.html',
                           planlar=planlar,
                           durum=durum,
                           arama=arama)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = RehberlikPlaniForm()
    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}')
                                for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()]

    if form.validate_on_submit():
        plan = RehberlikPlani(
            ogrenci_id=form.ogrenci_id.data,
            rehber_id=current_user.id,
            baslik=form.baslik.data,
            hedefler=form.hedefler.data,
            uygulanacak_yontemler=form.uygulanacak_yontemler.data,
            baslangic_tarihi=form.baslangic_tarihi.data,
            bitis_tarihi=form.bitis_tarihi.data,
            durum=form.durum.data,
            degerlendirme=form.degerlendirme.data,
        )
        db.session.add(plan)
        db.session.commit()
        flash('Rehberlik plani basariyla olusturuldu.', 'success')
        return redirect(url_for('rehberlik.plan.liste'))

    return render_template('rehberlik/plan_form.html',
                           form=form, baslik='Yeni Rehberlik Plani')


@bp.route('/<int:plan_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(plan_id):
    plan = RehberlikPlani.query.get_or_404(plan_id)
    return render_template('rehberlik/plan_detay.html', plan=plan)


@bp.route('/<int:plan_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(plan_id):
    plan = RehberlikPlani.query.get_or_404(plan_id)
    form = RehberlikPlaniForm(obj=plan)
    form.ogrenci_id.choices = [(o.id, f'{o.ogrenci_no} - {o.tam_ad}')
                                for o in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()]

    if form.validate_on_submit():
        plan.ogrenci_id = form.ogrenci_id.data
        plan.baslik = form.baslik.data
        plan.hedefler = form.hedefler.data
        plan.uygulanacak_yontemler = form.uygulanacak_yontemler.data
        plan.baslangic_tarihi = form.baslangic_tarihi.data
        plan.bitis_tarihi = form.bitis_tarihi.data
        plan.durum = form.durum.data
        plan.degerlendirme = form.degerlendirme.data

        db.session.commit()
        flash('Rehberlik plani basariyla guncellendi.', 'success')
        return redirect(url_for('rehberlik.plan.detay', plan_id=plan.id))

    return render_template('rehberlik/plan_form.html',
                           form=form, baslik='Rehberlik Plani Duzenle')


@bp.route('/<int:plan_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(plan_id):
    plan = RehberlikPlani.query.get_or_404(plan_id)
    baslik = plan.baslik
    db.session.delete(plan)
    db.session.commit()
    flash(f'"{baslik}" plani silindi.', 'success')
    return redirect(url_for('rehberlik.plan.liste'))
