from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Ogrenci, Taksit, OdemePlani
from app.models.kayit import OgrenciKayit, Sube, VeliBilgisi
from app.models.not_defteri import OgrenciNot, Sinav
from app.models.devamsizlik import Devamsizlik
from app.models.duyurular import Duyuru
from app.models.online_sinav import OnlineSinav, SinavKatilim
from app.ogrenci_portal.helpers import (
    get_current_ogrenci, get_current_veli, get_ogrenci_sube
)
from app.extensions import db
from datetime import date, datetime, timedelta
from sqlalchemy import func

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    ogrenci = get_current_ogrenci()
    veli = get_current_veli()

    if not ogrenci:
        flash('Öğrenci kaydınız bulunamadı. Lütfen yönetim ile iletişime geçin.', 'warning')
        return render_template('ogrenci_portal/index.html',
                               ogrenci=None,
                               veli=veli,
                               sube=None,
                               ortalama=0,
                               devamsizlik_gun=0,
                               sinav_sayisi=0,
                               duyurular=[],
                               son_notlar=[],
                               yaklasan_online=[],
                               haftalik_devamsizlik=0,
                               bekleyen_taksit=0,
                               bekleyen_borc=0,
                               simdi=datetime.now())

    sube = get_ogrenci_sube(ogrenci)
    bugun = date.today()
    hafta_basi = bugun - timedelta(days=bugun.weekday())

    # Not ortalamasi
    notlar_all = OgrenciNot.query.filter(
        OgrenciNot.ogrenci_id == ogrenci.id,
        OgrenciNot.puan.isnot(None)
    ).all()
    ortalama = round(sum(n.puan for n in notlar_all) / len(notlar_all), 1) if notlar_all else 0

    # Devamsizlik
    devamsizlik_gun = db.session.query(
        func.count(func.distinct(Devamsizlik.tarih))
    ).filter(
        Devamsizlik.ogrenci_id == ogrenci.id,
        Devamsizlik.durum == 'devamsiz'
    ).scalar() or 0

    haftalik_devamsizlik = Devamsizlik.query.filter(
        Devamsizlik.ogrenci_id == ogrenci.id,
        Devamsizlik.durum == 'devamsiz',
        Devamsizlik.tarih >= hafta_basi
    ).count()

    # Sinav sayisi
    sinav_sayisi = OgrenciNot.query.filter_by(ogrenci_id=ogrenci.id).count()

    # Son 5 not (sinav tarihine gore)
    son_notlar = (OgrenciNot.query
                  .join(Sinav, OgrenciNot.sinav_id == Sinav.id)
                  .filter(OgrenciNot.ogrenci_id == ogrenci.id,
                          OgrenciNot.puan.isnot(None))
                  .order_by(Sinav.tarih.desc())
                  .limit(5)
                  .all())

    # Yaklasan online sinavlar (gelecek 14 gun, aktif)
    yaklasan_online = []
    if sube:
        yaklasan_online = OnlineSinav.query.filter(
            OnlineSinav.aktif.is_(True),
            OnlineSinav.sube_id == sube.id,
            OnlineSinav.baslangic_zamani >= datetime.now(),
            OnlineSinav.baslangic_zamani <= datetime.now() + timedelta(days=14)
        ).order_by(OnlineSinav.baslangic_zamani.asc()).limit(4).all()

    # Bekleyen taksit / borc
    bekleyen_taksit = Taksit.query.join(OdemePlani).filter(
        OdemePlani.ogrenci_id == ogrenci.id,
        OdemePlani.durum == 'aktif',
        Taksit.durum.in_(['beklemede', 'kismi_odendi', 'gecikti'])
    ).count()

    bekleyen_borc = db.session.query(
        func.coalesce(func.sum(Taksit.tutar - Taksit.odenen_tutar), 0)
    ).select_from(Taksit).join(OdemePlani).filter(
        OdemePlani.ogrenci_id == ogrenci.id,
        OdemePlani.durum == 'aktif',
        Taksit.durum.in_(['beklemede', 'kismi_odendi', 'gecikti'])
    ).scalar() or 0
    bekleyen_borc = float(bekleyen_borc)

    # Son duyurular
    duyurular = Duyuru.query.filter(
        Duyuru.aktif == True,  # noqa: E712
        db.or_(
            Duyuru.hedef_kitle == 'tumu',
            Duyuru.hedef_kitle == 'ogrenciler',
            Duyuru.hedef_kitle == 'veliler'
        )
    ).order_by(Duyuru.sabitlenmis.desc(),
               Duyuru.yayinlanma_tarihi.desc()).limit(5).all()

    return render_template('ogrenci_portal/index.html',
                           ogrenci=ogrenci,
                           veli=veli,
                           sube=sube,
                           ortalama=ortalama,
                           devamsizlik_gun=devamsizlik_gun,
                           haftalik_devamsizlik=haftalik_devamsizlik,
                           sinav_sayisi=sinav_sayisi,
                           son_notlar=son_notlar,
                           yaklasan_online=yaklasan_online,
                           bekleyen_taksit=bekleyen_taksit,
                           bekleyen_borc=bekleyen_borc,
                           duyurular=duyurular,
                           simdi=datetime.now())
