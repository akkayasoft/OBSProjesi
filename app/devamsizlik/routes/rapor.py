from flask import Blueprint, render_template, request
from flask_login import login_required
from datetime import date, timedelta
from sqlalchemy import func

from app.extensions import db
from app.models.muhasebe import Ogrenci
from app.models.kayit import Sube, OgrenciKayit
from app.models.devamsizlik import Devamsizlik
from app.devamsizlik.forms import DevamsizlikRaporForm

bp = Blueprint('rapor', __name__)


def _sube_choices():
    subeler = Sube.query.filter_by(aktif=True).all()
    choices = [(0, 'Tüm Sınıflar')]
    for s in subeler:
        choices.append((s.id, s.tam_ad))
    return choices


@bp.route('/')
@login_required
def index():
    """Devamsızlık raporları ana sayfası."""
    form = DevamsizlikRaporForm(request.args, meta={'csrf': False})
    form.sube_id.choices = _sube_choices()

    # Varsayılan tarih aralığı: bu ay
    if not form.baslangic.data:
        form.baslangic.data = date.today().replace(day=1)
    if not form.bitis.data:
        form.bitis.data = date.today()

    baslangic = form.baslangic.data
    bitis = form.bitis.data
    sube_id = form.sube_id.data or 0

    # Sorgu
    query = Devamsizlik.query.filter(
        Devamsizlik.tarih >= baslangic,
        Devamsizlik.tarih <= bitis
    )
    if sube_id:
        query = query.filter_by(sube_id=sube_id)

    kayitlar = query.order_by(Devamsizlik.tarih.desc(), Devamsizlik.ders_saati).all()

    # Öğrenci bazlı özet
    ogrenci_ozet = {}
    for k in kayitlar:
        if k.ogrenci_id not in ogrenci_ozet:
            ogrenci_ozet[k.ogrenci_id] = {
                'ogrenci': k.ogrenci,
                'sube': k.sube,
                'devamsiz': 0,
                'gec': 0,
                'izinli': 0,
                'raporlu': 0,
                'toplam': 0,
                'gunler': set(),
            }
        ozet = ogrenci_ozet[k.ogrenci_id]
        ozet[k.durum] = ozet.get(k.durum, 0) + 1
        ozet['toplam'] += 1
        if k.durum == 'devamsiz':
            ozet['gunler'].add(k.tarih)

    # Sırala: en çok devamsız olan üstte
    ogrenci_listesi = sorted(
        ogrenci_ozet.values(),
        key=lambda x: x['devamsiz'],
        reverse=True
    )

    # Genel istatistikler
    toplam_devamsiz = sum(o['devamsiz'] for o in ogrenci_listesi)
    toplam_gec = sum(o['gec'] for o in ogrenci_listesi)
    toplam_izinli = sum(o['izinli'] for o in ogrenci_listesi)
    toplam_raporlu = sum(o['raporlu'] for o in ogrenci_listesi)

    # Kritik devamsızlık (20 ders saatini aşanlar)
    kritik_ogrenciler = [o for o in ogrenci_listesi if o['devamsiz'] >= 20]

    # Günlük dağılım (Chart.js için)
    gun_sayilari = {}
    for k in kayitlar:
        gun_str = k.tarih.strftime('%d.%m')
        if gun_str not in gun_sayilari:
            gun_sayilari[gun_str] = 0
        if k.durum == 'devamsiz':
            gun_sayilari[gun_str] += 1

    chart_labels = list(reversed(list(gun_sayilari.keys())))
    chart_data = list(reversed(list(gun_sayilari.values())))

    return render_template('devamsizlik/rapor/index.html',
                           form=form,
                           ogrenci_listesi=ogrenci_listesi,
                           toplam_devamsiz=toplam_devamsiz,
                           toplam_gec=toplam_gec,
                           toplam_izinli=toplam_izinli,
                           toplam_raporlu=toplam_raporlu,
                           kritik_ogrenciler=kritik_ogrenciler,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           baslangic=baslangic,
                           bitis=bitis)


@bp.route('/sinif/<int:sube_id>')
@login_required
def sinif_rapor(sube_id):
    """Sınıf bazlı devamsızlık raporu."""
    sube = Sube.query.get_or_404(sube_id)

    baslangic = request.args.get('baslangic')
    bitis = request.args.get('bitis')

    if baslangic:
        baslangic = date.fromisoformat(baslangic)
    else:
        baslangic = date.today().replace(day=1)
    if bitis:
        bitis = date.fromisoformat(bitis)
    else:
        bitis = date.today()

    # Aktif öğrenciler
    aktif_kayitlar = OgrenciKayit.query.filter_by(
        sube_id=sube_id, durum='aktif'
    ).all()
    ogrenciler = [k.ogrenci for k in aktif_kayitlar]
    ogrenciler.sort(key=lambda o: (o.soyad, o.ad))

    # Her öğrenci için devamsızlık sayıları
    ogrenci_verileri = []
    for ogr in ogrenciler:
        kayitlar = Devamsizlik.query.filter(
            Devamsizlik.ogrenci_id == ogr.id,
            Devamsizlik.sube_id == sube_id,
            Devamsizlik.tarih >= baslangic,
            Devamsizlik.tarih <= bitis
        ).all()

        devamsiz = sum(1 for k in kayitlar if k.durum == 'devamsiz')
        gec = sum(1 for k in kayitlar if k.durum == 'gec')
        izinli = sum(1 for k in kayitlar if k.durum == 'izinli')
        raporlu = sum(1 for k in kayitlar if k.durum == 'raporlu')

        ogrenci_verileri.append({
            'ogrenci': ogr,
            'devamsiz': devamsiz,
            'gec': gec,
            'izinli': izinli,
            'raporlu': raporlu,
            'toplam': devamsiz + gec + izinli + raporlu,
        })

    return render_template('devamsizlik/rapor/sinif_rapor.html',
                           sube=sube, ogrenci_verileri=ogrenci_verileri,
                           baslangic=baslangic, bitis=bitis)
