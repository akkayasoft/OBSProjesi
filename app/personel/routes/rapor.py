from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.muhasebe import Personel
from app.models.personel import PersonelIzin

bp = Blueprint('rapor', __name__)


@bp.route('/')
@login_required
@role_required('admin',)
def index():
    # Genel istatistikler
    toplam_personel = Personel.query.count()
    aktif_personel = Personel.query.filter_by(aktif=True).count()
    pasif_personel = toplam_personel - aktif_personel

    # Bekleyen izinler
    bekleyen_izin = PersonelIzin.query.filter_by(durum='beklemede').count()

    # Departman dağılımı
    departman_query = db.session.query(
        Personel.departman,
        db.func.count(Personel.id)
    ).filter(
        Personel.aktif == True,
        Personel.departman.isnot(None),
        Personel.departman != ''
    ).group_by(Personel.departman).all()

    departman_labels = [d[0] for d in departman_query]
    departman_values = [d[1] for d in departman_query]

    # Çalışma türü dağılımı
    calisma_turu_query = db.session.query(
        Personel.calisma_turu,
        db.func.count(Personel.id)
    ).filter(Personel.aktif == True).group_by(Personel.calisma_turu).all()

    turu_map = {'tam_zamanli': 'Tam Zamanlı', 'yari_zamanli': 'Yarı Zamanlı', 'sozlesmeli': 'Sözleşmeli'}
    calisma_labels = [turu_map.get(c[0], c[0]) for c in calisma_turu_query]
    calisma_values = [c[1] for c in calisma_turu_query]

    # İzin türü dağılımı
    izin_turu_query = db.session.query(
        PersonelIzin.izin_turu,
        db.func.count(PersonelIzin.id)
    ).filter(PersonelIzin.durum == 'onaylandi').group_by(PersonelIzin.izin_turu).all()

    turu_izin_map = {
        'yillik': 'Yıllık', 'saglik': 'Sağlık', 'mazeret': 'Mazeret',
        'ucretsiz': 'Ücretsiz', 'idari': 'İdari'
    }
    izin_labels = [turu_izin_map.get(i[0], i[0]) for i in izin_turu_query]
    izin_values = [i[1] for i in izin_turu_query]

    # Toplam izin gün sayısı (onaylanmış)
    toplam_izin_gun = db.session.query(
        db.func.sum(PersonelIzin.gun_sayisi)
    ).filter(PersonelIzin.durum == 'onaylandi').scalar() or 0

    return render_template('personel/rapor/index.html',
                           toplam_personel=toplam_personel,
                           aktif_personel=aktif_personel,
                           pasif_personel=pasif_personel,
                           bekleyen_izin=bekleyen_izin,
                           toplam_izin_gun=toplam_izin_gun,
                           departman_labels=departman_labels,
                           departman_values=departman_values,
                           calisma_labels=calisma_labels,
                           calisma_values=calisma_values,
                           izin_labels=izin_labels,
                           izin_values=izin_values)
