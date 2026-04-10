from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.iletisim import Mesaj
from app.models.user import User
from app.iletisim.forms import MesajForm
from datetime import datetime

bp = Blueprint('mesaj', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def gelen_kutusu():
    page = request.args.get('page', 1, type=int)

    mesajlar = Mesaj.query.filter(
        Mesaj.alici_id == current_user.id,
        Mesaj.silindi_alici == False
    ).order_by(
        Mesaj.okundu.asc(),
        Mesaj.created_at.desc()
    ).paginate(page=page, per_page=20)

    return render_template('iletisim/gelen_kutusu.html', mesajlar=mesajlar)


@bp.route('/giden')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def giden_kutusu():
    page = request.args.get('page', 1, type=int)

    mesajlar = Mesaj.query.filter(
        Mesaj.gonderen_id == current_user.id,
        Mesaj.silindi_gonderen == False
    ).order_by(Mesaj.created_at.desc()).paginate(page=page, per_page=20)

    return render_template('iletisim/giden_kutusu.html', mesajlar=mesajlar)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def yeni():
    form = MesajForm()

    # Kullanıcı listesini doldur
    kullanicilar = User.query.filter(
        User.id != current_user.id,
        User.aktif == True
    ).order_by(User.ad, User.soyad).all()
    form.alici_id.choices = [(u.id, u.tam_ad) for u in kullanicilar]

    if form.validate_on_submit():
        mesaj = Mesaj(
            gonderen_id=current_user.id,
            alici_id=form.alici_id.data,
            konu=form.konu.data,
            icerik=form.icerik.data,
        )
        db.session.add(mesaj)
        db.session.commit()
        flash('Mesaj başarıyla gönderildi.', 'success')
        return redirect(url_for('iletisim.mesaj.giden_kutusu'))

    return render_template('iletisim/mesaj_yaz.html', form=form, baslik='Yeni Mesaj')


@bp.route('/<int:mesaj_id>')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def oku(mesaj_id):
    mesaj = Mesaj.query.get_or_404(mesaj_id)

    # Sadece gönderen veya alıcı görebilir
    if mesaj.alici_id != current_user.id and mesaj.gonderen_id != current_user.id:
        flash('Bu mesajı görüntüleme yetkiniz yok.', 'danger')
        return redirect(url_for('iletisim.mesaj.gelen_kutusu'))

    # Okundu olarak işaretle
    if mesaj.alici_id == current_user.id and not mesaj.okundu:
        mesaj.okundu = True
        mesaj.okunma_tarihi = datetime.utcnow()
        db.session.commit()

    return render_template('iletisim/mesaj_oku.html', mesaj=mesaj)


@bp.route('/<int:mesaj_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def sil(mesaj_id):
    mesaj = Mesaj.query.get_or_404(mesaj_id)

    if mesaj.alici_id == current_user.id:
        mesaj.silindi_alici = True
        db.session.commit()
        flash('Mesaj silindi.', 'success')
        return redirect(url_for('iletisim.mesaj.gelen_kutusu'))
    elif mesaj.gonderen_id == current_user.id:
        mesaj.silindi_gonderen = True
        db.session.commit()
        flash('Mesaj silindi.', 'success')
        return redirect(url_for('iletisim.mesaj.giden_kutusu'))
    else:
        flash('Bu mesajı silme yetkiniz yok.', 'danger')
        return redirect(url_for('iletisim.mesaj.gelen_kutusu'))


@bp.route('/<int:mesaj_id>/yanitla', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def yanitla(mesaj_id):
    orijinal = Mesaj.query.get_or_404(mesaj_id)

    if orijinal.alici_id != current_user.id and orijinal.gonderen_id != current_user.id:
        flash('Bu mesajı yanıtlama yetkiniz yok.', 'danger')
        return redirect(url_for('iletisim.mesaj.gelen_kutusu'))

    form = MesajForm()

    # Kullanıcı listesini doldur
    kullanicilar = User.query.filter(
        User.id != current_user.id,
        User.aktif == True
    ).order_by(User.ad, User.soyad).all()
    form.alici_id.choices = [(u.id, u.tam_ad) for u in kullanicilar]

    if request.method == 'GET':
        # Yanıt alıcısı orijinal gönderen
        yanit_alici = orijinal.gonderen_id if orijinal.alici_id == current_user.id else orijinal.alici_id
        form.alici_id.data = yanit_alici
        form.konu.data = f"Re: {orijinal.konu}" if not orijinal.konu.startswith('Re: ') else orijinal.konu

    if form.validate_on_submit():
        mesaj = Mesaj(
            gonderen_id=current_user.id,
            alici_id=form.alici_id.data,
            konu=form.konu.data,
            icerik=form.icerik.data,
        )
        db.session.add(mesaj)
        db.session.commit()
        flash('Yanıt başarıyla gönderildi.', 'success')
        return redirect(url_for('iletisim.mesaj.gelen_kutusu'))

    return render_template('iletisim/mesaj_yaz.html',
                           form=form, baslik='Yanıtla', orijinal=orijinal)
