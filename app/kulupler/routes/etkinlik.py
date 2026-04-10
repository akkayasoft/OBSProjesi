from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.kulupler import Kulup, KulupEtkinlik, KulupUyelik, KulupDevamsizlik
from app.kulupler.forms import KulupEtkinlikForm

bp = Blueprint('etkinlik', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    page = request.args.get('page', 1, type=int)
    kulup_id = request.args.get('kulup_id', '', type=str)

    query = KulupEtkinlik.query

    if kulup_id:
        query = query.filter(KulupEtkinlik.kulup_id == int(kulup_id))

    etkinlikler = query.order_by(KulupEtkinlik.tarih.desc()).paginate(
        page=page, per_page=20
    )

    kulupler = Kulup.query.filter_by(aktif=True).order_by(Kulup.ad).all()

    return render_template('kulupler/etkinlik_listesi.html',
                           etkinlikler=etkinlikler,
                           kulupler=kulupler,
                           secili_kulup_id=kulup_id)


@bp.route('/<int:etkinlik_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(etkinlik_id):
    etkinlik = KulupEtkinlik.query.get_or_404(etkinlik_id)
    form = KulupEtkinlikForm(obj=etkinlik)

    if form.validate_on_submit():
        etkinlik.baslik = form.baslik.data
        etkinlik.aciklama = form.aciklama.data
        etkinlik.tarih = form.tarih.data
        etkinlik.konum = form.konum.data
        etkinlik.tur = form.tur.data
        etkinlik.durum = form.durum.data
        db.session.commit()
        flash('Etkinlik basariyla guncellendi.', 'success')
        return redirect(url_for('kulupler.etkinlik.liste'))

    return render_template('kulupler/etkinlik_form.html',
                           form=form, baslik='Etkinlik Duzenle',
                           kulup=etkinlik.kulup)


@bp.route('/<int:etkinlik_id>/sil', methods=['POST'])
@login_required
@role_required('admin')
def sil(etkinlik_id):
    etkinlik = KulupEtkinlik.query.get_or_404(etkinlik_id)
    db.session.delete(etkinlik)
    db.session.commit()
    flash('Etkinlik basariyla silindi.', 'success')
    return redirect(url_for('kulupler.etkinlik.liste'))


@bp.route('/<int:etkinlik_id>/yoklama', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yoklama(etkinlik_id):
    etkinlik = KulupEtkinlik.query.get_or_404(etkinlik_id)
    kulup = etkinlik.kulup

    # Aktif uyeleri al
    uyeler = KulupUyelik.query.filter_by(
        kulup_id=kulup.id, durum='aktif'
    ).all()

    if request.method == 'POST':
        for uyelik in uyeler:
            durum = request.form.get(f'durum_{uyelik.ogrenci_id}', 'katilmadi')
            mevcut = KulupDevamsizlik.query.filter_by(
                etkinlik_id=etkinlik.id,
                ogrenci_id=uyelik.ogrenci_id
            ).first()
            if mevcut:
                mevcut.durum = durum
            else:
                db.session.add(KulupDevamsizlik(
                    etkinlik_id=etkinlik.id,
                    ogrenci_id=uyelik.ogrenci_id,
                    durum=durum,
                ))
        db.session.commit()
        flash('Yoklama basariyla kaydedildi.', 'success')
        return redirect(url_for('kulupler.etkinlik.liste'))

    # Mevcut yoklama kayitlarini al
    mevcut_kayitlar = {}
    for kayit in KulupDevamsizlik.query.filter_by(etkinlik_id=etkinlik.id).all():
        mevcut_kayitlar[kayit.ogrenci_id] = kayit.durum

    return render_template('kulupler/yoklama.html',
                           etkinlik=etkinlik, kulup=kulup,
                           uyeler=uyeler, mevcut_kayitlar=mevcut_kayitlar)
