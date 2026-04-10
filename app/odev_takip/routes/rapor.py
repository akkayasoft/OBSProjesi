from flask import Blueprint, render_template, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.not_defteri import OdevTakip, OdevTeslim
from app.models.ders_dagitimi import Ders
from app.models.muhasebe import Ogrenci
from app.models.kayit import Sinif, Sube, OgrenciKayit

bp = Blueprint('rapor', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    rapor_turu = request.args.get('rapor_turu', 'ogrenci')
    ders_id = request.args.get('ders_id', type=int)
    sube_id = request.args.get('sube_id', type=int)

    dersler = Ders.query.filter_by(aktif=True).order_by(Ders.ad).all()
    subeler = Sube.query.join(Sube.sinif).filter(
        Sube.aktif == True  # noqa: E712
    ).order_by(Sinif.seviye, Sube.ad).all()

    rapor_verileri = []

    if rapor_turu == 'ogrenci':
        # Ogrenci bazli: en cok eksik odev olan ogrenciler
        query = db.session.query(
            Ogrenci.id,
            Ogrenci.ogrenci_no,
            Ogrenci.ad,
            Ogrenci.soyad,
            db.func.count(OdevTeslim.id).label('toplam_odev'),
            db.func.sum(
                db.case(
                    (OdevTeslim.durum == 'teslim_edilmedi', 1),
                    else_=0
                )
            ).label('eksik_odev'),
            db.func.sum(
                db.case(
                    (OdevTeslim.durum == 'teslim_edildi', 1),
                    else_=0
                )
            ).label('teslim_edilen'),
            db.func.avg(
                db.case(
                    (OdevTeslim.puan.isnot(None), OdevTeslim.puan),
                    else_=None
                )
            ).label('ortalama_puan')
        ).join(OdevTeslim, OdevTeslim.ogrenci_id == Ogrenci.id
        ).join(OdevTakip, OdevTakip.id == OdevTeslim.odev_id
        ).filter(OdevTakip.aktif == True)  # noqa: E712

        if ders_id:
            query = query.filter(OdevTakip.ders_id == ders_id)
        if sube_id:
            query = query.filter(OdevTakip.sube_id == sube_id)

        rapor_verileri = query.group_by(
            Ogrenci.id, Ogrenci.ogrenci_no, Ogrenci.ad, Ogrenci.soyad
        ).order_by(db.desc('eksik_odev')).limit(50).all()

    elif rapor_turu == 'ders':
        # Ders bazli rapor
        query = db.session.query(
            Ders.id,
            Ders.kod,
            Ders.ad,
            db.func.count(db.distinct(OdevTakip.id)).label('toplam_odev'),
            db.func.count(OdevTeslim.id).label('toplam_teslim'),
            db.func.sum(
                db.case(
                    (OdevTeslim.durum == 'teslim_edildi', 1),
                    else_=0
                )
            ).label('teslim_edilen'),
            db.func.avg(
                db.case(
                    (OdevTeslim.puan.isnot(None), OdevTeslim.puan),
                    else_=None
                )
            ).label('ortalama_puan')
        ).join(OdevTakip, OdevTakip.ders_id == Ders.id
        ).join(OdevTeslim, OdevTeslim.odev_id == OdevTakip.id
        ).filter(OdevTakip.aktif == True)  # noqa: E712

        rapor_verileri = query.group_by(
            Ders.id, Ders.kod, Ders.ad
        ).order_by(Ders.ad).all()

    elif rapor_turu == 'sinif':
        # Sinif/sube bazli rapor
        query = db.session.query(
            Sube.id,
            db.func.count(db.distinct(OdevTakip.id)).label('toplam_odev'),
            db.func.count(OdevTeslim.id).label('toplam_teslim'),
            db.func.sum(
                db.case(
                    (OdevTeslim.durum == 'teslim_edildi', 1),
                    else_=0
                )
            ).label('teslim_edilen'),
            db.func.avg(
                db.case(
                    (OdevTeslim.puan.isnot(None), OdevTeslim.puan),
                    else_=None
                )
            ).label('ortalama_puan')
        ).join(OdevTakip, OdevTakip.sube_id == Sube.id
        ).join(OdevTeslim, OdevTeslim.odev_id == OdevTakip.id
        ).filter(OdevTakip.aktif == True)  # noqa: E712

        results = query.group_by(Sube.id).all()

        # Sube bilgilerini ekle
        rapor_verileri = []
        for r in results:
            sube = Sube.query.get(r.id)
            if sube:
                rapor_verileri.append({
                    'sube': sube,
                    'toplam_odev': r.toplam_odev,
                    'toplam_teslim': r.toplam_teslim,
                    'teslim_edilen': r.teslim_edilen or 0,
                    'ortalama_puan': round(r.ortalama_puan, 1) if r.ortalama_puan else 0,
                    'teslim_orani': round((r.teslim_edilen or 0) / r.toplam_teslim * 100, 1) if r.toplam_teslim > 0 else 0
                })

    return render_template('odev_takip/rapor.html',
                           rapor_turu=rapor_turu,
                           rapor_verileri=rapor_verileri,
                           dersler=dersler,
                           subeler=subeler,
                           ders_id=ders_id,
                           sube_id=sube_id)


@bp.route('/ogrenci/<int:ogrenci_id>')
@login_required
@role_required('admin', 'ogretmen')
def ogrenci_rapor(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)

    # Ogrencinin tum odev teslimleri
    teslimler = OdevTeslim.query.join(OdevTakip).filter(
        OdevTeslim.ogrenci_id == ogrenci_id,
        OdevTakip.aktif == True  # noqa: E712
    ).order_by(OdevTakip.son_teslim_tarihi.desc()).all()

    toplam = len(teslimler)
    teslim_edilen = sum(1 for t in teslimler if t.durum == 'teslim_edildi')
    geciken = sum(1 for t in teslimler if t.durum == 'gecikti')
    eksik = sum(1 for t in teslimler if t.durum == 'teslim_edilmedi')
    tamamlanma = round(teslim_edilen / toplam * 100, 1) if toplam > 0 else 0

    # Puan ortalamasi
    puanli = [t for t in teslimler if t.puan is not None]
    puan_ortalamasi = round(sum(t.puan for t in puanli) / len(puanli), 1) if puanli else 0

    # Ogrencinin sinifi
    kayit = OgrenciKayit.query.filter_by(ogrenci_id=ogrenci_id, durum='aktif').first()
    sube = kayit.sube if kayit else None

    return render_template('odev_takip/ogrenci_rapor.html',
                           ogrenci=ogrenci,
                           sube=sube,
                           teslimler=teslimler,
                           toplam=toplam,
                           teslim_edilen=teslim_edilen,
                           geciken=geciken,
                           eksik=eksik,
                           tamamlanma=tamamlanma,
                           puan_ortalamasi=puan_ortalamasi)
