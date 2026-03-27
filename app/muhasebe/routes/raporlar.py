from datetime import date, timedelta
from io import BytesIO
from flask import Blueprint, render_template, request, send_file, jsonify
from flask_login import login_required
from sqlalchemy import func, extract
from app.extensions import db
from app.models.muhasebe import (
    GelirGiderKaydi, GelirGiderKategorisi,
    Taksit, Odeme, OdemePlani, Ogrenci,
    PersonelOdemeKaydi, Personel, BankaHesabi
)

bp = Blueprint('raporlar', __name__)


@bp.route('/')
@login_required
def genel():
    bugun = date.today()
    yil = request.args.get('yil', bugun.year, type=int)
    ay = request.args.get('ay', bugun.month, type=int)

    # Aylık gelir/gider özeti
    aylik_gelir = db.session.query(
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
    ).filter(
        GelirGiderKaydi.tur == 'gelir',
        extract('year', GelirGiderKaydi.tarih) == yil,
        extract('month', GelirGiderKaydi.tarih) == ay
    ).scalar()

    aylik_gider = db.session.query(
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
    ).filter(
        GelirGiderKaydi.tur == 'gider',
        extract('year', GelirGiderKaydi.tarih) == yil,
        extract('month', GelirGiderKaydi.tarih) == ay
    ).scalar()

    # Kategorilere göre dağılım
    gelir_kategorileri = db.session.query(
        GelirGiderKategorisi.ad,
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0).label('toplam')
    ).join(GelirGiderKaydi).filter(
        GelirGiderKaydi.tur == 'gelir',
        extract('year', GelirGiderKaydi.tarih) == yil,
        extract('month', GelirGiderKaydi.tarih) == ay
    ).group_by(GelirGiderKategorisi.ad).all()

    gider_kategorileri = db.session.query(
        GelirGiderKategorisi.ad,
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0).label('toplam')
    ).join(GelirGiderKaydi).filter(
        GelirGiderKaydi.tur == 'gider',
        extract('year', GelirGiderKaydi.tarih) == yil,
        extract('month', GelirGiderKaydi.tarih) == ay
    ).group_by(GelirGiderKategorisi.ad).all()

    # Yıllık trend (12 aylık)
    aylik_trend = []
    for m in range(1, 13):
        g = db.session.query(
            func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
        ).filter(
            GelirGiderKaydi.tur == 'gelir',
            extract('year', GelirGiderKaydi.tarih) == yil,
            extract('month', GelirGiderKaydi.tarih) == m
        ).scalar()

        gd = db.session.query(
            func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
        ).filter(
            GelirGiderKaydi.tur == 'gider',
            extract('year', GelirGiderKaydi.tarih) == yil,
            extract('month', GelirGiderKaydi.tarih) == m
        ).scalar()

        aylik_trend.append({'ay': m, 'gelir': float(g), 'gider': float(gd)})

    # Öğrenci borç durumu
    toplam_ogrenci_borc = 0
    ogrenci_sayisi = Ogrenci.query.filter_by(aktif=True).count()
    borclu_ogrenci = 0

    for ogrenci in Ogrenci.query.filter_by(aktif=True).all():
        borc = ogrenci.toplam_borc
        toplam_ogrenci_borc += borc
        if borc > 0:
            borclu_ogrenci += 1

    # Personel maliyet
    aylik_personel_maliyet = db.session.query(
        func.coalesce(func.sum(PersonelOdemeKaydi.tutar), 0)
    ).filter(
        extract('year', PersonelOdemeKaydi.tarih) == yil,
        extract('month', PersonelOdemeKaydi.tarih) == ay
    ).scalar()

    ay_isimleri = ['', 'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
                   'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']

    return render_template('muhasebe/raporlar/genel.html',
                           yil=yil, ay=ay,
                           ay_adi=ay_isimleri[ay],
                           aylik_gelir=float(aylik_gelir),
                           aylik_gider=float(aylik_gider),
                           gelir_kategorileri=gelir_kategorileri,
                           gider_kategorileri=gider_kategorileri,
                           aylik_trend=aylik_trend,
                           toplam_ogrenci_borc=toplam_ogrenci_borc,
                           ogrenci_sayisi=ogrenci_sayisi,
                           borclu_ogrenci=borclu_ogrenci,
                           aylik_personel_maliyet=float(aylik_personel_maliyet),
                           ay_isimleri=ay_isimleri)


@bp.route('/export/<rapor_turu>')
@login_required
def export(rapor_turu):
    try:
        from openpyxl import Workbook
    except ImportError:
        from flask import flash
        flash('Excel export için openpyxl kütüphanesi gerekli.', 'danger')
        return ''

    wb = Workbook()
    ws = wb.active

    bugun = date.today()
    yil = request.args.get('yil', bugun.year, type=int)
    ay = request.args.get('ay', bugun.month, type=int)

    if rapor_turu == 'gelir-gider':
        ws.title = 'Gelir Gider Raporu'
        ws.append(['Tarih', 'Tür', 'Kategori', 'Açıklama', 'Belge No', 'Tutar'])

        kayitlar = GelirGiderKaydi.query.filter(
            extract('year', GelirGiderKaydi.tarih) == yil,
            extract('month', GelirGiderKaydi.tarih) == ay
        ).order_by(GelirGiderKaydi.tarih).all()

        for k in kayitlar:
            ws.append([
                k.tarih.strftime('%d.%m.%Y'),
                k.tur.title(),
                k.kategori.ad,
                k.aciklama or '',
                k.belge_no or '',
                float(k.tutar)
            ])

    elif rapor_turu == 'ogrenci-borc':
        ws.title = 'Öğrenci Borç Raporu'
        ws.append(['Öğrenci No', 'Ad Soyad', 'Sınıf', 'Toplam Borç'])

        for ogrenci in Ogrenci.query.filter_by(aktif=True).order_by(Ogrenci.sinif, Ogrenci.soyad).all():
            borc = ogrenci.toplam_borc
            if borc > 0:
                ws.append([ogrenci.ogrenci_no, ogrenci.tam_ad, ogrenci.sinif or '', borc])

    elif rapor_turu == 'personel-maliyet':
        ws.title = 'Personel Maliyet Raporu'
        ws.append(['Sicil No', 'Ad Soyad', 'Pozisyon', 'Dönem', 'Tutar'])

        odemeler = PersonelOdemeKaydi.query.filter(
            extract('year', PersonelOdemeKaydi.tarih) == yil,
            extract('month', PersonelOdemeKaydi.tarih) == ay
        ).join(Personel).order_by(Personel.soyad).all()

        for o in odemeler:
            ws.append([
                o.personel.sicil_no, o.personel.tam_ad,
                o.personel.pozisyon or '', o.donem, float(o.tutar)
            ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    dosya_adi = f'{rapor_turu}_{yil}_{ay:02d}.xlsx'
    return send_file(output, as_attachment=True, download_name=dosya_adi,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
