from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.utils import role_required
from app.extensions import db
from app.models.yurt import YurtOda, YurtKayit, YurtYoklama, YurtYoklamaDetay
from app.models.muhasebe import Personel
from datetime import date

bp = Blueprint('yoklama', __name__)


@bp.route('/')
@login_required
@role_required('admin')
def index():
    odalar = YurtOda.query.filter_by(durum='aktif').order_by(YurtOda.oda_no).all()
    return render_template('yurt/yoklama.html', odalar=odalar)


@bp.route('/<int:oda_id>/al', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def al(oda_id):
    oda = YurtOda.query.get_or_404(oda_id)
    kayitlar = oda.kayitlar.filter_by(aktif=True).all()

    if request.method == 'POST':
        yoklama_turu = request.form.get('yoklama_turu', 'aksam')
        personel = Personel.query.filter(
            Personel.ad == current_user.ad, Personel.soyad == current_user.soyad
        ).first()

        yoklama = YurtYoklama(
            oda_id=oda.id, tarih=date.today(),
            yoklama_turu=yoklama_turu,
            yapan_id=personel.id if personel else 1,
        )
        db.session.add(yoklama)
        db.session.flush()

        for kayit in kayitlar:
            durum_val = request.form.get(f'durum_{kayit.ogrenci_id}', 'mevcut')
            detay = YurtYoklamaDetay(
                yoklama_id=yoklama.id,
                ogrenci_id=kayit.ogrenci_id,
                durum=durum_val,
            )
            db.session.add(detay)

        db.session.commit()
        flash(f'Oda {oda.oda_no} yoklamasi alindi.', 'success')
        return redirect(url_for('yurt.yoklama.index'))

    return render_template('yurt/yoklama_al.html', oda=oda, kayitlar=kayitlar)


@bp.route('/gecmis')
@login_required
@role_required('admin')
def gecmis():
    page = request.args.get('page', 1, type=int)
    yoklamalar = YurtYoklama.query.order_by(
        YurtYoklama.tarih.desc(), YurtYoklama.created_at.desc()
    ).paginate(page=page, per_page=20)
    return render_template('yurt/yoklama_gecmis.html', yoklamalar=yoklamalar)
