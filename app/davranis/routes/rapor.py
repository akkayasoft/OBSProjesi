from flask import Blueprint, render_template, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.davranis import DavranisDeğerlendirme
from app.models.muhasebe import Ogrenci
from app.models.kayit import Sinif
from sqlalchemy import func, extract, cast, Integer
from datetime import date, timedelta

bp = Blueprint('rapor', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def genel():
    sinif_id = request.args.get('sinif_id', '', type=str)
    baslangic = request.args.get('baslangic', '')
    bitis = request.args.get('bitis', '')

    # Varsayilan tarih araligi: son 30 gun
    if not baslangic:
        baslangic_tarih = date.today() - timedelta(days=30)
        baslangic = baslangic_tarih.strftime('%Y-%m-%d')
    else:
        from datetime import datetime
        baslangic_tarih = datetime.strptime(baslangic, '%Y-%m-%d').date()

    if not bitis:
        bitis_tarih = date.today()
        bitis = bitis_tarih.strftime('%Y-%m-%d')
    else:
        from datetime import datetime
        bitis_tarih = datetime.strptime(bitis, '%Y-%m-%d').date()

    query = DavranisDeğerlendirme.query.filter(
        DavranisDeğerlendirme.tarih >= baslangic_tarih,
        DavranisDeğerlendirme.tarih <= bitis_tarih
    )

    if sinif_id:
        query = query.filter(DavranisDeğerlendirme.sinif_id == int(sinif_id))

    # Genel istatistikler
    toplam = query.count()
    olumlu = query.filter(DavranisDeğerlendirme.tur == 'olumlu').count()
    olumsuz = query.filter(DavranisDeğerlendirme.tur == 'olumsuz').count()
    toplam_puan = db.session.query(func.coalesce(func.sum(DavranisDeğerlendirme.puan), 0)).filter(
        DavranisDeğerlendirme.tarih >= baslangic_tarih,
        DavranisDeğerlendirme.tarih <= bitis_tarih
    )
    if sinif_id:
        toplam_puan = toplam_puan.filter(DavranisDeğerlendirme.sinif_id == int(sinif_id))
    toplam_puan = toplam_puan.scalar()

    # Kategoriye gore dagilim
    kategori_dagilim = db.session.query(
        DavranisDeğerlendirme.kategori,
        func.count(DavranisDeğerlendirme.id)
    ).filter(
        DavranisDeğerlendirme.tarih >= baslangic_tarih,
        DavranisDeğerlendirme.tarih <= bitis_tarih
    )
    if sinif_id:
        kategori_dagilim = kategori_dagilim.filter(DavranisDeğerlendirme.sinif_id == int(sinif_id))
    kategori_dagilim = kategori_dagilim.group_by(DavranisDeğerlendirme.kategori).all()

    kategori_labels = []
    kategori_values = []
    kategori_map = {
        'akademik': 'Akademik', 'sosyal': 'Sosyal', 'disiplin': 'Disiplin',
        'saglik': 'Saglik', 'diger': 'Diger'
    }
    for kat, sayi in kategori_dagilim:
        kategori_labels.append(kategori_map.get(kat, kat))
        kategori_values.append(sayi)

    # Aylik trend (son 6 ay) — DB-bagimsiz: yil ve ay'i ayri extract edip
    # Python tarafinda 'YYYY-MM' olarak birlestir. (strftime sadece SQLite'ta var.)
    yil_col = cast(extract('year', DavranisDeğerlendirme.tarih), Integer)
    ay_col = cast(extract('month', DavranisDeğerlendirme.tarih), Integer)
    aylik_trend_q = db.session.query(
        yil_col.label('yil'),
        ay_col.label('ay'),
        DavranisDeğerlendirme.tur,
        func.count(DavranisDeğerlendirme.id)
    ).filter(
        DavranisDeğerlendirme.tarih >= date.today() - timedelta(days=180)
    )
    if sinif_id:
        aylik_trend_q = aylik_trend_q.filter(DavranisDeğerlendirme.sinif_id == int(sinif_id))
    aylik_trend_rows = aylik_trend_q.group_by(
        yil_col, ay_col, DavranisDeğerlendirme.tur
    ).all()

    # (yil, ay, tur, sayi) -> 'YYYY-MM' format
    aylik_trend = [
        (f'{int(yil):04d}-{int(ay):02d}', tur, sayi)
        for yil, ay, tur, sayi in aylik_trend_rows
    ]

    # Trend verisi isle
    aylar = sorted(set(row[0] for row in aylik_trend))
    olumlu_trend = []
    olumsuz_trend = []
    for ay in aylar:
        o_sayi = next((row[2] for row in aylik_trend if row[0] == ay and row[1] == 'olumlu'), 0)
        n_sayi = next((row[2] for row in aylik_trend if row[0] == ay and row[1] == 'olumsuz'), 0)
        olumlu_trend.append(o_sayi)
        olumsuz_trend.append(n_sayi)

    # Sinif bazli ozet
    sinif_ozet = db.session.query(
        Sinif.ad,
        func.count(DavranisDeğerlendirme.id),
        func.coalesce(func.sum(DavranisDeğerlendirme.puan), 0)
    ).join(
        DavranisDeğerlendirme, DavranisDeğerlendirme.sinif_id == Sinif.id
    ).filter(
        DavranisDeğerlendirme.tarih >= baslangic_tarih,
        DavranisDeğerlendirme.tarih <= bitis_tarih
    ).group_by(Sinif.ad).all()

    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.ad).all()

    return render_template('davranis/rapor.html',
                           siniflar=siniflar,
                           sinif_id=sinif_id,
                           baslangic=baslangic,
                           bitis=bitis,
                           toplam=toplam,
                           olumlu=olumlu,
                           olumsuz=olumsuz,
                           toplam_puan=toplam_puan,
                           kategori_labels=kategori_labels,
                           kategori_values=kategori_values,
                           aylar=aylar,
                           olumlu_trend=olumlu_trend,
                           olumsuz_trend=olumsuz_trend,
                           sinif_ozet=sinif_ozet)


@bp.route('/ogrenci/<int:ogrenci_id>')
@login_required
@role_required('admin', 'ogretmen')
def ogrenci_rapor(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)

    kayitlar = DavranisDeğerlendirme.query.filter_by(
        ogrenci_id=ogrenci_id
    ).order_by(DavranisDeğerlendirme.tarih.desc()).all()

    # Istatistikler
    toplam = len(kayitlar)
    olumlu = sum(1 for k in kayitlar if k.tur == 'olumlu')
    olumsuz = sum(1 for k in kayitlar if k.tur == 'olumsuz')
    toplam_puan = sum(k.puan for k in kayitlar)

    # Kategoriye gore dagilim
    kategori_map = {
        'akademik': 'Akademik', 'sosyal': 'Sosyal', 'disiplin': 'Disiplin',
        'saglik': 'Saglik', 'diger': 'Diger'
    }
    kategori_sayac = {}
    for k in kayitlar:
        label = kategori_map.get(k.kategori, k.kategori)
        kategori_sayac[label] = kategori_sayac.get(label, 0) + 1
    kategori_labels = list(kategori_sayac.keys())
    kategori_values = list(kategori_sayac.values())

    # Puan trendi (tarih bazli)
    puan_tarihler = []
    puan_degerleri = []
    kumulatif = 0
    for k in sorted(kayitlar, key=lambda x: x.tarih):
        kumulatif += k.puan
        puan_tarihler.append(k.tarih.strftime('%d.%m.%Y'))
        puan_degerleri.append(kumulatif)

    return render_template('davranis/ogrenci_rapor.html',
                           ogrenci=ogrenci,
                           kayitlar=kayitlar,
                           toplam=toplam,
                           olumlu=olumlu,
                           olumsuz=olumsuz,
                           toplam_puan=toplam_puan,
                           kategori_labels=kategori_labels,
                           kategori_values=kategori_values,
                           puan_tarihler=puan_tarihler,
                           puan_degerleri=puan_degerleri)
