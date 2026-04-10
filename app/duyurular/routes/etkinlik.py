import calendar
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.duyurular import Etkinlik
from app.duyurular.forms import EtkinlikForm

bp = Blueprint('etkinlik', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def takvim():
    today = date.today()
    yil = request.args.get('yil', today.year, type=int)
    ay = request.args.get('ay', today.month, type=int)

    # Ay sınırlarını kontrol et
    if ay < 1:
        ay = 12
        yil -= 1
    elif ay > 12:
        ay = 1
        yil += 1

    # Takvim verisini oluştur
    cal = calendar.Calendar(firstweekday=0)  # Pazartesi başlangıç
    ay_gunleri = cal.monthdayscalendar(yil, ay)

    # Bu aydaki etkinlikleri getir
    ay_baslangic = datetime(yil, ay, 1)
    if ay == 12:
        ay_bitis = datetime(yil + 1, 1, 1)
    else:
        ay_bitis = datetime(yil, ay + 1, 1)

    etkinlikler = Etkinlik.query.filter(
        Etkinlik.aktif == True,
        Etkinlik.baslangic_tarihi >= ay_baslangic,
        Etkinlik.baslangic_tarihi < ay_bitis
    ).order_by(Etkinlik.baslangic_tarihi).all()

    # Etkinlikleri gün numarasına göre grupla
    etkinlik_gunleri = {}
    for e in etkinlikler:
        gun = e.baslangic_tarihi.day
        if gun not in etkinlik_gunleri:
            etkinlik_gunleri[gun] = []
        etkinlik_gunleri[gun].append(e)

    # Önceki ve sonraki ay
    if ay == 1:
        onceki_yil, onceki_ay = yil - 1, 12
    else:
        onceki_yil, onceki_ay = yil, ay - 1

    if ay == 12:
        sonraki_yil, sonraki_ay = yil + 1, 1
    else:
        sonraki_yil, sonraki_ay = yil, ay + 1

    ay_isimleri = [
        '', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
        'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık'
    ]

    return render_template('duyurular/etkinlik_takvim.html',
                           ay_gunleri=ay_gunleri,
                           etkinlik_gunleri=etkinlik_gunleri,
                           yil=yil,
                           ay=ay,
                           ay_adi=ay_isimleri[ay],
                           onceki_yil=onceki_yil,
                           onceki_ay=onceki_ay,
                           sonraki_yil=sonraki_yil,
                           sonraki_ay=sonraki_ay,
                           bugun=today)


@bp.route('/liste')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def liste():
    page = request.args.get('page', 1, type=int)
    tur = request.args.get('tur', '')

    query = Etkinlik.query.filter_by(aktif=True)

    if tur:
        query = query.filter(Etkinlik.tur == tur)

    etkinlikler = query.order_by(
        Etkinlik.baslangic_tarihi.desc()
    ).paginate(page=page, per_page=20)

    return render_template('duyurular/etkinlik_liste.html',
                           etkinlikler=etkinlikler,
                           tur=tur)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def yeni():
    form = EtkinlikForm()

    if form.validate_on_submit():
        etkinlik = Etkinlik(
            baslik=form.baslik.data,
            aciklama=form.aciklama.data or None,
            tur=form.tur.data,
            baslangic_tarihi=form.baslangic_tarihi.data,
            bitis_tarihi=form.bitis_tarihi.data,
            konum=form.konum.data or None,
            renk=form.renk.data,
            tum_gun=form.tum_gun.data,
            olusturan_id=current_user.id,
        )
        db.session.add(etkinlik)
        db.session.commit()
        flash('Etkinlik başarıyla oluşturuldu.', 'success')
        return redirect(url_for('duyurular.etkinlik.takvim'))

    return render_template('duyurular/etkinlik_form.html',
                           form=form, baslik='Yeni Etkinlik')


@bp.route('/<int:etkinlik_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def duzenle(etkinlik_id):
    etkinlik = Etkinlik.query.get_or_404(etkinlik_id)
    form = EtkinlikForm(obj=etkinlik)

    if form.validate_on_submit():
        etkinlik.baslik = form.baslik.data
        etkinlik.aciklama = form.aciklama.data or None
        etkinlik.tur = form.tur.data
        etkinlik.baslangic_tarihi = form.baslangic_tarihi.data
        etkinlik.bitis_tarihi = form.bitis_tarihi.data
        etkinlik.konum = form.konum.data or None
        etkinlik.renk = form.renk.data
        etkinlik.tum_gun = form.tum_gun.data

        db.session.commit()
        flash('Etkinlik başarıyla güncellendi.', 'success')
        return redirect(url_for('duyurular.etkinlik.takvim'))

    return render_template('duyurular/etkinlik_form.html',
                           form=form, baslik='Etkinlik Düzenle')


@bp.route('/<int:etkinlik_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def sil(etkinlik_id):
    etkinlik = Etkinlik.query.get_or_404(etkinlik_id)
    baslik = etkinlik.baslik
    db.session.delete(etkinlik)
    db.session.commit()
    flash(f'"{baslik}" etkinliği silindi.', 'success')
    return redirect(url_for('duyurular.etkinlik.takvim'))


@bp.route('/api/events')
@login_required
@role_required('admin', 'ogretmen', 'veli', 'ogrenci', 'muhasebeci')
def api_events():
    """AJAX takvim için JSON API"""
    baslangic = request.args.get('start', '')
    bitis = request.args.get('end', '')

    query = Etkinlik.query.filter_by(aktif=True)

    if baslangic:
        try:
            baslangic_dt = datetime.fromisoformat(baslangic)
            query = query.filter(Etkinlik.baslangic_tarihi >= baslangic_dt)
        except ValueError:
            pass
    if bitis:
        try:
            bitis_dt = datetime.fromisoformat(bitis)
            query = query.filter(Etkinlik.bitis_tarihi <= bitis_dt)
        except ValueError:
            pass

    etkinlikler = query.order_by(Etkinlik.baslangic_tarihi).all()

    events = []
    for e in etkinlikler:
        events.append({
            'id': e.id,
            'title': e.baslik,
            'start': e.baslangic_tarihi.isoformat(),
            'end': e.bitis_tarihi.isoformat(),
            'color': e.renk,
            'allDay': e.tum_gun,
            'type': e.tur_str,
            'location': e.konum or '',
        })

    return jsonify(events)
