from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.etut import Etut, EtutKatilim
from app.models.muhasebe import Ogrenci
from app.models.kayit import OgrenciKayit
from app.etut.forms import EtutKatilimForm

bp = Blueprint('katilim', __name__)


@bp.route('/<int:etut_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yoklama(etut_id):
    etut = Etut.query.get_or_404(etut_id)
    form = EtutKatilimForm()

    if not form.tarih.data:
        form.tarih.data = date.today()

    # Sube varsa o subenin ogrencilerini getir, yoksa tum aktif ogrencileri
    if etut.sube_id:
        kayitlar = OgrenciKayit.query.filter_by(
            sube_id=etut.sube_id, durum='aktif'
        ).all()
        ogrenciler = [k.ogrenci for k in kayitlar if k.ogrenci and k.ogrenci.aktif]
    else:
        ogrenciler = Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.ad).all()

    if request.method == 'POST' and form.validate_on_submit():
        tarih = form.tarih.data

        # Mevcut kayitlari temizle (ayni tarih icin)
        EtutKatilim.query.filter_by(
            etut_id=etut.id, tarih=tarih
        ).delete()

        for ogrenci in ogrenciler:
            katildi = request.form.get(f'katilim_{ogrenci.id}') == 'on'
            aciklama = request.form.get(f'aciklama_{ogrenci.id}', '').strip()

            kayit = EtutKatilim(
                etut_id=etut.id,
                ogrenci_id=ogrenci.id,
                tarih=tarih,
                katildi=katildi,
                aciklama=aciklama if aciklama else None,
            )
            db.session.add(kayit)

        db.session.commit()
        flash('Katilim kaydi basariyla kaydedildi.', 'success')
        return redirect(url_for('etut.etut_yonetim.detay', etut_id=etut.id))

    # Secili tarih icin mevcut katilim kayitlarini getir
    tarih = form.tarih.data or date.today()
    mevcut_katilimlar = {}
    kayitlar = EtutKatilim.query.filter_by(
        etut_id=etut.id, tarih=tarih
    ).all()
    for k in kayitlar:
        mevcut_katilimlar[k.ogrenci_id] = k

    return render_template('etut/katilim.html',
                           etut=etut,
                           form=form,
                           ogrenciler=ogrenciler,
                           mevcut_katilimlar=mevcut_katilimlar)


@bp.route('/<int:etut_id>/gecmis')
@login_required
@role_required('admin', 'ogretmen')
def gecmis(etut_id):
    etut = Etut.query.get_or_404(etut_id)
    page = request.args.get('page', 1, type=int)

    # Tarihlere gore grupla
    tarihler = db.session.query(
        EtutKatilim.tarih,
        db.func.count(EtutKatilim.id).label('toplam'),
        db.func.sum(db.case((EtutKatilim.katildi.is_(True), 1), else_=0)).label('katilan'),
    ).filter(
        EtutKatilim.etut_id == etut.id
    ).group_by(
        EtutKatilim.tarih
    ).order_by(
        EtutKatilim.tarih.desc()
    ).paginate(page=page, per_page=20)

    return render_template('etut/katilim_gecmis.html',
                           etut=etut,
                           tarihler=tarihler)
