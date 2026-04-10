from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app.utils import role_required
from app.models.ders_dagitimi import DersProgrami, Ders
from app.models.kayit import Sube, Sinif

program_bp = Blueprint('program', __name__)

GUNLER = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma']
SAAT_ARALIKLARI = {
    1: '08:30 - 09:10',
    2: '09:20 - 10:00',
    3: '10:10 - 10:50',
    4: '11:00 - 11:40',
    5: '12:30 - 13:10',
    6: '13:20 - 14:00',
    7: '14:10 - 14:50',
    8: '15:00 - 15:40',
}


@program_bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    """Ders programı görüntüleme ana sayfa"""
    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.ad).all()
    subeler = Sube.query.filter_by(aktif=True).order_by(Sube.ad).all()
    return render_template('ders_programi/index.html',
                           siniflar=siniflar,
                           subeler=subeler)


@program_bp.route('/goruntule')
@login_required
@role_required('admin', 'ogretmen')
def goruntule():
    """Şubeye göre ders programı görüntüle"""
    sube_id = request.args.get('sube_id', type=int)
    donem = request.args.get('donem', '')

    if not sube_id:
        siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.ad).all()
        subeler = Sube.query.filter_by(aktif=True).order_by(Sube.ad).all()
        return render_template('ders_programi/index.html',
                               siniflar=siniflar,
                               subeler=subeler,
                               hata='Lütfen bir şube seçiniz.')

    sube = Sube.query.get_or_404(sube_id)

    query = DersProgrami.query.filter_by(sube_id=sube_id, aktif=True)
    if donem:
        query = query.filter_by(donem=donem)

    programlar = query.all()

    # Programı tablo formatına dönüştür
    tablo = {}
    for gun in GUNLER:
        tablo[gun] = {}
        for saat in range(1, 9):
            tablo[gun][saat] = None

    for p in programlar:
        if p.gun in tablo and p.ders_saati in tablo[p.gun]:
            tablo[p.gun][p.ders_saati] = p

    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.ad).all()
    subeler = Sube.query.filter_by(aktif=True).order_by(Sube.ad).all()

    return render_template('ders_programi/goruntule.html',
                           sube=sube,
                           tablo=tablo,
                           gunler=GUNLER,
                           saat_araliklari=SAAT_ARALIKLARI,
                           donem=donem,
                           siniflar=siniflar,
                           subeler=subeler)


@program_bp.route('/ogretmen')
@login_required
@role_required('admin', 'ogretmen')
def ogretmen_programi():
    """Öğretmenin haftalık ders programı"""
    from flask_login import current_user
    from app.models.muhasebe import Personel

    ogretmen_id = request.args.get('ogretmen_id', type=int)

    # Eğer ogretmen_id verilmemişse ve kullanıcı öğretmense kendi programını göster
    if not ogretmen_id and current_user.rol == 'ogretmen':
        personel = Personel.query.filter_by(
            eposta=current_user.email
        ).first()
        if personel:
            ogretmen_id = personel.id

    if not ogretmen_id:
        ogretmenler = Personel.query.filter_by(aktif=True).order_by(
            Personel.ad, Personel.soyad
        ).all()
        return render_template('ders_programi/ogretmen_sec.html',
                               ogretmenler=ogretmenler)

    ogretmen = Personel.query.get_or_404(ogretmen_id)
    donem = request.args.get('donem', '')

    query = DersProgrami.query.filter_by(ogretmen_id=ogretmen_id, aktif=True)
    if donem:
        query = query.filter_by(donem=donem)

    programlar = query.all()

    # Programı tablo formatına dönüştür
    tablo = {}
    for gun in GUNLER:
        tablo[gun] = {}
        for saat in range(1, 9):
            tablo[gun][saat] = None

    for p in programlar:
        if p.gun in tablo and p.ders_saati in tablo[p.gun]:
            tablo[p.gun][p.ders_saati] = p

    return render_template('ders_programi/ogretmen_programi.html',
                           ogretmen=ogretmen,
                           tablo=tablo,
                           gunler=GUNLER,
                           saat_araliklari=SAAT_ARALIKLARI,
                           donem=donem)


@program_bp.route('/yazdir/<int:sube_id>')
@login_required
@role_required('admin', 'ogretmen')
def yazdir(sube_id):
    """Ders programını yazdırma görünümü"""
    sube = Sube.query.get_or_404(sube_id)
    donem = request.args.get('donem', '')

    query = DersProgrami.query.filter_by(sube_id=sube_id, aktif=True)
    if donem:
        query = query.filter_by(donem=donem)

    programlar = query.all()

    tablo = {}
    for gun in GUNLER:
        tablo[gun] = {}
        for saat in range(1, 9):
            tablo[gun][saat] = None

    for p in programlar:
        if p.gun in tablo and p.ders_saati in tablo[p.gun]:
            tablo[p.gun][p.ders_saati] = p

    return render_template('ders_programi/yazdir.html',
                           sube=sube,
                           tablo=tablo,
                           gunler=GUNLER,
                           saat_araliklari=SAAT_ARALIKLARI,
                           donem=donem)
