from flask import Blueprint, render_template, flash
from flask_login import login_required, current_user
from app.utils import role_required
from app.models.muhasebe import Ogrenci
from app.models.kayit import OgrenciKayit, Sube
from app.models.not_defteri import OgrenciNot, Sinav
from app.models.devamsizlik import Devamsizlik
from app.models.duyurular import Duyuru
from app.models.online_sinav import OnlineSinav, SinavKatilim
from app.extensions import db
from datetime import date, datetime

bp = Blueprint('dashboard', __name__)


def get_current_ogrenci():
    """Mevcut kullaniciya ait ogrenci kaydini bul."""
    if current_user.rol == 'veli':
        # Veli icin soyada gore ogrenci bul
        return Ogrenci.query.filter_by(soyad=current_user.soyad, aktif=True).first()
    # Ogrenci veya admin icin ad+soyad ile esle
    return Ogrenci.query.filter_by(ad=current_user.ad, soyad=current_user.soyad, aktif=True).first()


def get_ogrenci_sube(ogrenci):
    """Ogrencinin aktif kaydindaki subeyi bul."""
    kayit = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci.id, durum='aktif'
    ).first()
    if kayit:
        return kayit.sube
    return None


@bp.route('/')
@login_required
@role_required('ogrenci', 'veli', 'admin')
def index():
    ogrenci = get_current_ogrenci()
    if not ogrenci:
        flash('Ogrenci kaydiniz bulunamadi.', 'warning')
        return render_template('ogrenci_portal/index.html',
                               ogrenci=None,
                               sube=None,
                               ortalama=0,
                               devamsizlik_gun=0,
                               sinav_sayisi=0,
                               duyurular=[])

    sube = get_ogrenci_sube(ogrenci)

    # Not ortalamasi
    notlar = OgrenciNot.query.filter(
        OgrenciNot.ogrenci_id == ogrenci.id,
        OgrenciNot.puan.isnot(None)
    ).all()
    ortalama = round(sum(n.puan for n in notlar) / len(notlar), 1) if notlar else 0

    # Devamsizlik gun sayisi
    devamsizlik_gun = db.session.query(
        db.func.count(db.func.distinct(Devamsizlik.tarih))
    ).filter(
        Devamsizlik.ogrenci_id == ogrenci.id,
        Devamsizlik.durum == 'devamsiz'
    ).scalar() or 0

    # Sinav sayisi
    sinav_sayisi = OgrenciNot.query.filter_by(ogrenci_id=ogrenci.id).count()

    # Son duyurular
    duyurular = Duyuru.query.filter(
        Duyuru.aktif == True,  # noqa: E712
        db.or_(
            Duyuru.hedef_kitle == 'tumu',
            Duyuru.hedef_kitle == 'ogrenciler',
            Duyuru.hedef_kitle == 'veliler'
        )
    ).order_by(Duyuru.yayinlanma_tarihi.desc()).limit(5).all()

    return render_template('ogrenci_portal/index.html',
                           ogrenci=ogrenci,
                           sube=sube,
                           ortalama=ortalama,
                           devamsizlik_gun=devamsizlik_gun,
                           sinav_sayisi=sinav_sayisi,
                           duyurular=duyurular)
