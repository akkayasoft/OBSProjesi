from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.kulupler import Kulup, KulupUyelik
from app.models.muhasebe import Ogrenci
from app.kulupler.forms import KulupUyelikForm

bp = Blueprint('uyelik', __name__)


@bp.route('/kulup/<int:kulup_id>/uyeler')
@login_required
@role_required('admin', 'ogretmen')
def liste(kulup_id):
    kulup = Kulup.query.get_or_404(kulup_id)
    uyeler = KulupUyelik.query.filter_by(kulup_id=kulup.id).order_by(
        KulupUyelik.gorev, KulupUyelik.created_at
    ).all()

    return render_template('kulupler/uye_listesi.html',
                           kulup=kulup, uyeler=uyeler)


@bp.route('/kulup/<int:kulup_id>/uye-ekle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def ekle(kulup_id):
    kulup = Kulup.query.get_or_404(kulup_id)
    form = KulupUyelikForm()

    # Mevcut uyeleri haric tut
    mevcut_ogrenci_idler = [u.ogrenci_id for u in
                            KulupUyelik.query.filter_by(kulup_id=kulup.id).all()]
    ogrenciler = Ogrenci.query.filter(
        Ogrenci.aktif == True,
        ~Ogrenci.id.in_(mevcut_ogrenci_idler) if mevcut_ogrenci_idler else True
    ).order_by(Ogrenci.ad).all()
    form.ogrenci_id.choices = [(o.id, f'{o.ad} {o.soyad} ({o.ogrenci_no})') for o in ogrenciler]

    if form.validate_on_submit():
        # Kontenjan kontrolu
        aktif_uye_sayisi = KulupUyelik.query.filter_by(
            kulup_id=kulup.id, durum='aktif'
        ).count()
        if aktif_uye_sayisi >= kulup.kontenjan:
            flash('Kulup kontenjani dolu.', 'danger')
            return redirect(url_for('kulupler.uyelik.liste', kulup_id=kulup.id))

        uyelik = KulupUyelik(
            kulup_id=kulup.id,
            ogrenci_id=form.ogrenci_id.data,
            gorev=form.gorev.data,
            durum='aktif',
        )
        db.session.add(uyelik)
        db.session.commit()
        flash('Uye basariyla eklendi.', 'success')
        return redirect(url_for('kulupler.uyelik.liste', kulup_id=kulup.id))

    return render_template('kulupler/uye_ekle.html',
                           form=form, kulup=kulup)


@bp.route('/uyelik/<int:uyelik_id>/cikar', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def cikar(uyelik_id):
    uyelik = KulupUyelik.query.get_or_404(uyelik_id)
    kulup_id = uyelik.kulup_id
    uyelik.durum = 'ayrildi'
    db.session.commit()
    flash('Uye basariyla cikarildi.', 'success')
    return redirect(url_for('kulupler.uyelik.liste', kulup_id=kulup_id))


@bp.route('/uyelik/<int:uyelik_id>/gorev', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def gorev_degistir(uyelik_id):
    uyelik = KulupUyelik.query.get_or_404(uyelik_id)
    yeni_gorev = request.form.get('gorev', 'uye')
    if yeni_gorev in ('uye', 'baskan', 'baskan_yardimcisi', 'sekreter'):
        uyelik.gorev = yeni_gorev
        db.session.commit()
        flash('Gorev basariyla guncellendi.', 'success')
    return redirect(url_for('kulupler.uyelik.liste', kulup_id=uyelik.kulup_id))
