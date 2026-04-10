from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.envanter import Demirbas, DemirbasHareket
from app.models.muhasebe import Personel
from app.envanter.forms import HareketForm

bp = Blueprint('hareket', __name__)


@bp.route('/<int:demirbas_id>/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def yeni(demirbas_id):
    d = Demirbas.query.get_or_404(demirbas_id)
    form = HareketForm()
    personeller = Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    form.yeni_sorumlu_id.choices = [(0, 'Seciniz')] + [(p.id, f'{p.ad} {p.soyad}') for p in personeller]

    if form.validate_on_submit():
        hareket = DemirbasHareket(
            demirbas_id=d.id,
            hareket_tipi=form.hareket_tipi.data,
            eski_konum=d.konum,
            yeni_konum=form.yeni_konum.data or d.konum,
            eski_sorumlu_id=d.sorumlu_id,
            yeni_sorumlu_id=form.yeni_sorumlu_id.data if form.yeni_sorumlu_id.data != 0 else None,
            tarih=form.tarih.data,
            aciklama=form.aciklama.data,
        )
        if form.yeni_konum.data:
            d.konum = form.yeni_konum.data
        if form.yeni_sorumlu_id.data and form.yeni_sorumlu_id.data != 0:
            d.sorumlu_id = form.yeni_sorumlu_id.data
        if form.hareket_tipi.data == 'ariza':
            d.durum = 'arizali'
        elif form.hareket_tipi.data == 'hurda':
            d.durum = 'hurda'

        db.session.add(hareket)
        db.session.commit()
        flash('Hareket kaydedildi.', 'success')
        return redirect(url_for('envanter.demirbas.detay', demirbas_id=d.id))

    return render_template('envanter/hareket_form.html', form=form, demirbas=d)
