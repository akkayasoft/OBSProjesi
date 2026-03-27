from datetime import date, timedelta
from flask import render_template
from flask_login import login_required
from sqlalchemy import func
from app.main import main_bp
from app.extensions import db
from app.models.muhasebe import (
    GelirGiderKaydi, Taksit, BankaHesabi,
    Odeme, PersonelOdemeKaydi
)


@main_bp.route('/')
@login_required
def dashboard():
    bugun = date.today()
    ay_basi = bugun.replace(day=1)

    # Aylık gelir
    aylik_gelir = db.session.query(
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
    ).filter(
        GelirGiderKaydi.tur == 'gelir',
        GelirGiderKaydi.tarih >= ay_basi
    ).scalar()

    # Aylık gider
    aylik_gider = db.session.query(
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
    ).filter(
        GelirGiderKaydi.tur == 'gider',
        GelirGiderKaydi.tarih >= ay_basi
    ).scalar()

    # Geciken taksitler
    geciken_taksitler = Taksit.query.filter(
        Taksit.durum.in_(['beklemede', 'kismi_odendi']),
        Taksit.vade_tarihi < bugun
    ).count()

    # Toplam banka bakiyesi
    toplam_bakiye = db.session.query(
        func.coalesce(func.sum(BankaHesabi.bakiye), 0)
    ).filter(BankaHesabi.aktif == True).scalar()  # noqa: E712

    # Son 10 işlem (ödemeler)
    son_odemeler = Odeme.query.order_by(Odeme.tarih.desc()).limit(10).all()

    # Son 10 gelir/gider
    son_gelir_gider = GelirGiderKaydi.query.order_by(
        GelirGiderKaydi.tarih.desc()
    ).limit(10).all()

    return render_template('main/dashboard.html',
                           aylik_gelir=float(aylik_gelir),
                           aylik_gider=float(aylik_gider),
                           geciken_taksitler=geciken_taksitler,
                           toplam_bakiye=float(toplam_bakiye),
                           son_odemeler=son_odemeler,
                           son_gelir_gider=son_gelir_gider)
