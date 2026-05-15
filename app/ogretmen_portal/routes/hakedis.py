"""Ogretmen portali — kendi aylik ders saati ve hak edisi gorunumu."""
import calendar
from datetime import date
from decimal import Decimal

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import extract, func

from app.utils import role_required
from app.extensions import db
from app.models.muhasebe import OgretmenDersSaati, PersonelOdemeKaydi
from app.ogretmen_hakedis import (_gecerli_ay, _ay_str, _ay_etiket,
                                  _komsu_aylar, HAKEDIS_ISARET)

bp = Blueprint('hakedis', __name__)


@bp.route('/hakedis/')
@bp.route('/hakedis/<ay>')
@login_required
@role_required('ogretmen', 'admin')
def index(ay=None):
    yil, ay_no = _gecerli_ay(ay)
    donem = _ay_str(yil, ay_no)
    onceki_ay, sonraki_ay = _komsu_aylar(yil, ay_no)
    gun_sayisi = calendar.monthrange(yil, ay_no)[1]

    personel = getattr(current_user, 'personel', None)
    if personel is None:
        return render_template(
            'ogretmen_portal/hakedis.html',
            personel=None, donem=donem, ay_etiket=_ay_etiket(yil, ay_no),
            onceki_ay=onceki_ay, sonraki_ay=sonraki_ay,
        )

    kayitlar = OgretmenDersSaati.query.filter(
        OgretmenDersSaati.personel_id == personel.id,
        extract('year', OgretmenDersSaati.tarih) == yil,
        extract('month', OgretmenDersSaati.tarih) == ay_no,
    ).all()
    gunler = {k.tarih.day: k.saat for k in kayitlar}
    toplam_saat = Decimal(str(sum((Decimal(str(k.saat)) for k in kayitlar),
                                  Decimal('0'))))
    ucret = Decimal(str(personel.saatlik_ucret or 0))
    tutar = toplam_saat * ucret

    odeme = PersonelOdemeKaydi.query.filter(
        PersonelOdemeKaydi.personel_id == personel.id,
        PersonelOdemeKaydi.donem == donem,
        PersonelOdemeKaydi.aciklama.ilike(f'%{HAKEDIS_ISARET}%'),
    ).first()

    return render_template(
        'ogretmen_portal/hakedis.html',
        personel=personel, donem=donem, ay_etiket=_ay_etiket(yil, ay_no),
        onceki_ay=onceki_ay, sonraki_ay=sonraki_ay,
        gunler=gunler, gun_listesi=list(range(1, gun_sayisi + 1)),
        toplam_saat=toplam_saat, saatlik_ucret=ucret, tutar=tutar,
        odeme=odeme,
    )
