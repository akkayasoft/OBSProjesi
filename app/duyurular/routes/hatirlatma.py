from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from datetime import datetime, timedelta
from app.extensions import db
from app.models.duyurular import Hatirlatma
from app.duyurular.forms import HatirlatmaForm

bp = Blueprint('hatirlatma', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def liste():
    now = datetime.utcnow()
    bugun_basi = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yarin_basi = bugun_basi + timedelta(days=1)
    yarin_sonu = bugun_basi + timedelta(days=2)
    hafta_sonu = bugun_basi + timedelta(days=7)

    # Tüm hatırlatmalar
    tum_hatirlatmalar = Hatirlatma.query.filter(
        Hatirlatma.kullanici_id == current_user.id
    ).order_by(Hatirlatma.tamamlandi, Hatirlatma.tarih).all()

    # Gruplara ayır
    bugun = []
    yarin = []
    bu_hafta = []
    gelecek = []
    tamamlanan = []

    for h in tum_hatirlatmalar:
        if h.tamamlandi:
            tamamlanan.append(h)
        elif h.tarih < yarin_basi:
            bugun.append(h)
        elif h.tarih < yarin_sonu:
            yarin.append(h)
        elif h.tarih < hafta_sonu:
            bu_hafta.append(h)
        else:
            gelecek.append(h)

    return render_template('duyurular/hatirlatma.html',
                           bugun=bugun,
                           yarin=yarin,
                           bu_hafta=bu_hafta,
                           gelecek=gelecek,
                           tamamlanan=tamamlanan)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def yeni():
    form = HatirlatmaForm()

    if form.validate_on_submit():
        hatirlatma = Hatirlatma(
            baslik=form.baslik.data,
            aciklama=form.aciklama.data or None,
            tarih=form.tarih.data,
            oncelik=form.oncelik.data,
            kullanici_id=current_user.id,
        )
        db.session.add(hatirlatma)
        db.session.commit()
        flash('Hatırlatma başarıyla oluşturuldu.', 'success')
        return redirect(url_for('duyurular.hatirlatma.liste'))

    return render_template('duyurular/hatirlatma_form.html',
                           form=form, baslik='Yeni Hatırlatma')


@bp.route('/<int:hatirlatma_id>/tamamla', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def tamamla(hatirlatma_id):
    hatirlatma = Hatirlatma.query.get_or_404(hatirlatma_id)
    if hatirlatma.kullanici_id != current_user.id:
        flash('Bu hatırlatma size ait değil.', 'danger')
        return redirect(url_for('duyurular.hatirlatma.liste'))

    hatirlatma.tamamlandi = not hatirlatma.tamamlandi
    db.session.commit()
    durum = 'tamamlandı' if hatirlatma.tamamlandi else 'tekrar açıldı'
    flash(f'Hatırlatma {durum}.', 'success')
    return redirect(url_for('duyurular.hatirlatma.liste'))


@bp.route('/<int:hatirlatma_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def sil(hatirlatma_id):
    hatirlatma = Hatirlatma.query.get_or_404(hatirlatma_id)
    if hatirlatma.kullanici_id != current_user.id:
        flash('Bu hatırlatma size ait değil.', 'danger')
        return redirect(url_for('duyurular.hatirlatma.liste'))

    baslik = hatirlatma.baslik
    db.session.delete(hatirlatma)
    db.session.commit()
    flash(f'"{baslik}" hatırlatması silindi.', 'success')
    return redirect(url_for('duyurular.hatirlatma.liste'))
