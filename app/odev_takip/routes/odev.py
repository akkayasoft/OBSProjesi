from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.not_defteri import OdevTakip, OdevTeslim
from app.models.ders_dagitimi import Ders
from app.models.muhasebe import Ogrenci, Personel
from app.models.kayit import Sinif, Sube, OgrenciKayit
from app.odev_takip.forms import OdevForm, OdevTeslimForm

bp = Blueprint('odev', __name__)


@bp.route('/liste/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    ders_id = request.args.get('ders_id', type=int)
    sube_id = request.args.get('sube_id', type=int)
    durum = request.args.get('durum', '')
    tarih_baslangic = request.args.get('tarih_baslangic', '')
    tarih_bitis = request.args.get('tarih_bitis', '')
    page = request.args.get('page', 1, type=int)

    query = OdevTakip.query.filter_by(aktif=True)

    if ders_id:
        query = query.filter(OdevTakip.ders_id == ders_id)
    if sube_id:
        query = query.filter(OdevTakip.sube_id == sube_id)

    bugun = date.today()
    if durum == 'aktif':
        query = query.filter(OdevTakip.son_teslim_tarihi >= bugun)
    elif durum == 'gecikti':
        query = query.filter(OdevTakip.son_teslim_tarihi < bugun)

    if tarih_baslangic:
        try:
            from datetime import datetime
            t_bas = datetime.strptime(tarih_baslangic, '%Y-%m-%d').date()
            query = query.filter(OdevTakip.son_teslim_tarihi >= t_bas)
        except ValueError:
            pass
    if tarih_bitis:
        try:
            from datetime import datetime
            t_bit = datetime.strptime(tarih_bitis, '%Y-%m-%d').date()
            query = query.filter(OdevTakip.son_teslim_tarihi <= t_bit)
        except ValueError:
            pass

    odevler = query.order_by(OdevTakip.son_teslim_tarihi.desc()).paginate(page=page, per_page=20)

    dersler = Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    subeler = Sube.query.join(Sube.sinif).filter(
        Sube.aktif == True  # noqa: E712
    ).order_by(Sinif.seviye, Sube.ad).all()

    return render_template('odev_takip/odev_listesi.html',
                           odevler=odevler,
                           dersler=dersler,
                           subeler=subeler,
                           ders_id=ders_id,
                           sube_id=sube_id,
                           durum=durum,
                           tarih_baslangic=tarih_baslangic,
                           tarih_bitis=tarih_bitis)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yeni():
    form = OdevForm()

    form.ders_id.choices = [
        (d.id, f'{d.kod} - {d.ad}') for d in Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    ]
    form.sube_id.choices = [
        (s.id, s.tam_ad) for s in Sube.query.join(Sube.sinif).filter(
            Sube.aktif == True  # noqa: E712
        ).order_by(Sinif.seviye, Sube.ad).all()
    ]
    form.ogretmen_id.choices = [
        (p.id, f'{p.tam_ad} ({p.sicil_no})') for p in Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    ]

    if form.validate_on_submit():
        odev = OdevTakip(
            baslik=form.baslik.data,
            ders_id=form.ders_id.data,
            sube_id=form.sube_id.data,
            ogretmen_id=form.ogretmen_id.data,
            son_teslim_tarihi=form.son_teslim_tarihi.data,
            donem=form.donem.data,
            aciklama=form.aciklama.data or None,
        )
        db.session.add(odev)
        db.session.commit()

        # Subedeki ogrenciler icin teslim kayitlari olustur
        kayitlar = OgrenciKayit.query.filter_by(
            sube_id=odev.sube_id, durum='aktif'
        ).all()
        ogrenciler = [k.ogrenci for k in kayitlar]

        if not ogrenciler:
            ogrenciler = Ogrenci.query.filter_by(aktif=True).all()

        for ogr in ogrenciler:
            teslim = OdevTeslim(
                odev_id=odev.id,
                ogrenci_id=ogr.id,
                durum='teslim_edilmedi',
            )
            db.session.add(teslim)
        db.session.commit()

        flash('Odev basariyla olusturuldu.', 'success')
        return redirect(url_for('odev_takip.odev.liste'))

    return render_template('odev_takip/odev_form.html',
                           form=form, baslik='Yeni Odev')


@bp.route('/<int:odev_id>')
@login_required
@role_required('admin', 'ogretmen')
def detay(odev_id):
    odev = OdevTakip.query.get_or_404(odev_id)

    teslimler = odev.teslimler.all()
    toplam = len(teslimler)
    teslim_edilen = sum(1 for t in teslimler if t.durum == 'teslim_edildi')
    geciken = sum(1 for t in teslimler if t.durum == 'gecikti')
    teslim_edilmedi = sum(1 for t in teslimler if t.durum == 'teslim_edilmedi')

    tamamlanma = round(teslim_edilen / toplam * 100, 1) if toplam > 0 else 0

    # Puan ortalmasi
    puanli = [t for t in teslimler if t.puan is not None]
    puan_ortalamasi = round(sum(t.puan for t in puanli) / len(puanli), 1) if puanli else 0

    return render_template('odev_takip/odev_detay.html',
                           odev=odev,
                           teslimler=teslimler,
                           toplam=toplam,
                           teslim_edilen=teslim_edilen,
                           geciken=geciken,
                           teslim_edilmedi=teslim_edilmedi,
                           tamamlanma=tamamlanma,
                           puan_ortalamasi=puan_ortalamasi)


@bp.route('/<int:odev_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def duzenle(odev_id):
    odev = OdevTakip.query.get_or_404(odev_id)
    form = OdevForm(obj=odev)

    form.ders_id.choices = [
        (d.id, f'{d.kod} - {d.ad}') for d in Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    ]
    form.sube_id.choices = [
        (s.id, s.tam_ad) for s in Sube.query.join(Sube.sinif).filter(
            Sube.aktif == True  # noqa: E712
        ).order_by(Sinif.seviye, Sube.ad).all()
    ]
    form.ogretmen_id.choices = [
        (p.id, f'{p.tam_ad} ({p.sicil_no})') for p in Personel.query.filter_by(aktif=True).order_by(Personel.ad).all()
    ]

    if form.validate_on_submit():
        odev.baslik = form.baslik.data
        odev.ders_id = form.ders_id.data
        odev.sube_id = form.sube_id.data
        odev.ogretmen_id = form.ogretmen_id.data
        odev.son_teslim_tarihi = form.son_teslim_tarihi.data
        odev.donem = form.donem.data
        odev.aciklama = form.aciklama.data or None

        db.session.commit()
        flash('Odev bilgileri guncellendi.', 'success')
        return redirect(url_for('odev_takip.odev.detay', odev_id=odev.id))

    return render_template('odev_takip/odev_form.html',
                           form=form, baslik='Odev Duzenle')


@bp.route('/<int:odev_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def sil(odev_id):
    odev = OdevTakip.query.get_or_404(odev_id)
    baslik = odev.baslik
    db.session.delete(odev)
    db.session.commit()
    flash(f'"{baslik}" odevi silindi.', 'success')
    return redirect(url_for('odev_takip.odev.liste'))


@bp.route('/<int:odev_id>/teslim', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def teslim(odev_id):
    odev = OdevTakip.query.get_or_404(odev_id)
    form = OdevTeslimForm()

    teslimler = odev.teslimler.all()

    teslim_dict = {}
    for t in teslimler:
        teslim_dict[t.ogrenci_id] = t

    if request.method == 'POST' and form.validate():
        for t in teslimler:
            durum_val = request.form.get(f'durum_{t.ogrenci_id}', 'teslim_edilmedi')
            puan_str = request.form.get(f'puan_{t.ogrenci_id}', '').strip()
            aciklama = request.form.get(f'aciklama_{t.ogrenci_id}', '').strip()

            t.durum = durum_val
            if durum_val == 'teslim_edildi' and not t.teslim_tarihi:
                t.teslim_tarihi = date.today()
            elif durum_val == 'teslim_edilmedi':
                t.teslim_tarihi = None

            if puan_str:
                try:
                    t.puan = float(puan_str)
                except ValueError:
                    pass
            else:
                t.puan = None

            t.aciklama = aciklama or None

        db.session.commit()
        flash('Teslim durumlari guncellendi.', 'success')
        return redirect(url_for('odev_takip.odev.detay', odev_id=odev.id))

    return render_template('odev_takip/teslim.html',
                           odev=odev,
                           form=form,
                           teslimler=teslimler,
                           teslim_dict=teslim_dict)


@bp.route('/<int:odev_id>/istatistik')
@login_required
@role_required('admin', 'ogretmen')
def istatistik(odev_id):
    odev = OdevTakip.query.get_or_404(odev_id)

    teslimler = odev.teslimler.all()
    toplam = len(teslimler)
    teslim_edilen = [t for t in teslimler if t.durum == 'teslim_edildi']
    geciken = [t for t in teslimler if t.durum == 'gecikti']
    teslim_edilmedi = [t for t in teslimler if t.durum == 'teslim_edilmedi']

    tamamlanma = round(len(teslim_edilen) / toplam * 100, 1) if toplam > 0 else 0

    # Puan istatistikleri
    puanli = [t for t in teslimler if t.puan is not None]
    puan_ortalamasi = round(sum(t.puan for t in puanli) / len(puanli), 1) if puanli else 0
    en_yuksek = max((t.puan for t in puanli), default=0)
    en_dusuk = min((t.puan for t in puanli), default=0)

    # Puan dagilimi
    puan_araliklari = {
        '90-100': 0, '80-89': 0, '70-79': 0,
        '60-69': 0, '50-59': 0, '0-49': 0
    }
    for t in puanli:
        p = t.puan
        if p >= 90:
            puan_araliklari['90-100'] += 1
        elif p >= 80:
            puan_araliklari['80-89'] += 1
        elif p >= 70:
            puan_araliklari['70-79'] += 1
        elif p >= 60:
            puan_araliklari['60-69'] += 1
        elif p >= 50:
            puan_araliklari['50-59'] += 1
        else:
            puan_araliklari['0-49'] += 1

    return render_template('odev_takip/istatistik.html',
                           odev=odev,
                           toplam=toplam,
                           teslim_edilen=teslim_edilen,
                           geciken=geciken,
                           teslim_edilmedi=teslim_edilmedi,
                           tamamlanma=tamamlanma,
                           puan_ortalamasi=puan_ortalamasi,
                           en_yuksek=en_yuksek,
                           en_dusuk=en_dusuk,
                           puan_araliklari=puan_araliklari)
