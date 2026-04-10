from flask import Blueprint, render_template, request
from flask_login import login_required
from app.utils import role_required
from app.models.karne import Karne, KarneDersNotu
from app.models.muhasebe import Ogrenci

bp = Blueprint('transkript', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    arama = request.args.get('arama', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Ogrenci.query.filter_by(aktif=True)
    if arama:
        query = query.filter(
            Ogrenci.ad.ilike(f'%{arama}%') |
            Ogrenci.soyad.ilike(f'%{arama}%') |
            Ogrenci.ogrenci_no.ilike(f'%{arama}%')
        )

    ogrenciler = query.order_by(Ogrenci.ad).paginate(page=page, per_page=20)
    return render_template('karne/transkript_liste.html',
                           ogrenciler=ogrenciler,
                           arama=arama)


@bp.route('/<int:ogrenci_id>')
@login_required
@role_required('admin', 'ogretmen')
def goruntule(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    karneler = Karne.query.filter_by(ogrenci_id=ogrenci_id).order_by(
        Karne.ogretim_yili, Karne.donem
    ).all()

    # Her karne icin ders notlarini hazirla
    transkript_verileri = []
    genel_toplam = 0
    genel_sayi = 0
    for karne in karneler:
        ders_notlari = karne.ders_notlari.order_by(KarneDersNotu.ders_adi).all()
        transkript_verileri.append({
            'karne': karne,
            'ders_notlari': ders_notlari,
        })
        if karne.genel_ortalama:
            genel_toplam += karne.genel_ortalama
            genel_sayi += 1

    genel_kumulatif = round(genel_toplam / genel_sayi, 2) if genel_sayi > 0 else None

    return render_template('karne/transkript.html',
                           ogrenci=ogrenci,
                           transkript_verileri=transkript_verileri,
                           genel_kumulatif=genel_kumulatif)
