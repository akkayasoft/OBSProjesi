"""Ana sayfa (dashboard) — role-aware, zengin icerik."""
from datetime import date, datetime, timedelta
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from app.main import main_bp
from app.extensions import db
from app.models.muhasebe import (
    GelirGiderKaydi, Taksit, BankaHesabi,
    Odeme, PersonelOdemeKaydi, OdemePlani, Ogrenci, Personel
)
from app.models.user import User
from app.models.duyurular import Duyuru, Etkinlik
from app.models.bildirim import Bildirim
from app.models.devamsizlik import Devamsizlik
from app.models.personel import PersonelIzin
from app.models.rehberlik import Gorusme
from app.models.kayit import Sinif, OgrenciKayit


def _ay_gelir_gider(ay_basi):
    """Verilen ay icin (gelir, gider) tuple'i doner."""
    gelir = db.session.query(
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
    ).filter(
        GelirGiderKaydi.tur == 'gelir',
        GelirGiderKaydi.tarih >= ay_basi,
        GelirGiderKaydi.tarih < (ay_basi.replace(day=28) + timedelta(days=7)).replace(day=1)
    ).scalar()
    gider = db.session.query(
        func.coalesce(func.sum(GelirGiderKaydi.tutar), 0)
    ).filter(
        GelirGiderKaydi.tur == 'gider',
        GelirGiderKaydi.tarih >= ay_basi,
        GelirGiderKaydi.tarih < (ay_basi.replace(day=28) + timedelta(days=7)).replace(day=1)
    ).scalar()
    return float(gelir or 0), float(gider or 0)


def _son_n_ay_listesi(n=6):
    """Son n ayin (yil, ay, ay_basi) listesini doner (eski -> yeni)."""
    bugun = date.today()
    aylar = []
    yil, ay = bugun.year, bugun.month
    for _ in range(n):
        aylar.append((yil, ay, date(yil, ay, 1)))
        ay -= 1
        if ay == 0:
            ay = 12
            yil -= 1
    return list(reversed(aylar))


AY_ADLARI = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz',
             'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara']


@main_bp.route('/')
@login_required
def dashboard():
    # Ogrenci ve veli rollerini kendi portalina yonlendir
    if current_user.rol in ('ogrenci', 'veli'):
        return redirect(url_for('ogrenci_portal.dashboard.index'))

    bugun = date.today()
    ay_basi = bugun.replace(day=1)
    hafta_basi = bugun - timedelta(days=bugun.weekday())
    otuz_gun_sonra = bugun + timedelta(days=30)

    # ========== FINANSAL KPI'LAR (herkes icin sayisi uygun olanlar) ==========
    aylik_gelir, aylik_gider = _ay_gelir_gider(ay_basi)
    aylik_kar = aylik_gelir - aylik_gider

    # Bu ay alinan ogrenci odemeleri
    aylik_tahsilat = db.session.query(
        func.coalesce(func.sum(Odeme.tutar), 0)
    ).filter(
        Odeme.iptal_edildi.is_(False),
        Odeme.tarih >= ay_basi
    ).scalar() or 0
    aylik_tahsilat = float(aylik_tahsilat)

    geciken_taksitler = Taksit.query.filter(
        Taksit.durum.in_(['beklemede', 'kismi_odendi', 'gecikti']),
        Taksit.vade_tarihi < bugun
    ).count()

    geciken_tutar = db.session.query(
        func.coalesce(func.sum(Taksit.tutar - Taksit.odenen_tutar), 0)
    ).filter(
        Taksit.durum.in_(['beklemede', 'kismi_odendi', 'gecikti']),
        Taksit.vade_tarihi < bugun
    ).scalar() or 0
    geciken_tutar = float(geciken_tutar)

    toplam_bakiye = db.session.query(
        func.coalesce(func.sum(BankaHesabi.bakiye), 0)
    ).filter(BankaHesabi.aktif == True).scalar() or 0  # noqa: E712
    toplam_bakiye = float(toplam_bakiye)

    # 30 gun icinde vadesi gelecek taksitler
    yaklasan_taksit_sayi = Taksit.query.filter(
        Taksit.durum.in_(['beklemede', 'kismi_odendi']),
        Taksit.vade_tarihi >= bugun,
        Taksit.vade_tarihi <= otuz_gun_sonra
    ).count()

    # ========== KISI SAYILARI ==========
    toplam_ogrenci = Ogrenci.query.filter_by(aktif=True).count()
    toplam_personel = Personel.query.filter_by(aktif=True).count()
    toplam_sinif = Sinif.query.count()

    # ========== BU HAFTA / BUGUN ==========
    bugunku_devamsizlik = Devamsizlik.query.filter(
        Devamsizlik.tarih == bugun,
        Devamsizlik.durum == 'devamsiz'
    ).count()
    haftalik_devamsizlik = Devamsizlik.query.filter(
        Devamsizlik.tarih >= hafta_basi,
        Devamsizlik.durum == 'devamsiz'
    ).count()

    # Bekleyen personel izin basvurulari
    bekleyen_izin = PersonelIzin.query.filter_by(durum='beklemede').count()

    # Bu hafta planlanan rehberlik gorusmeleri
    haftalik_gorusme = Gorusme.query.filter(
        Gorusme.gorusme_tarihi >= datetime.combine(hafta_basi, datetime.min.time()),
        Gorusme.gorusme_tarihi < datetime.combine(hafta_basi + timedelta(days=7), datetime.min.time()),
        Gorusme.durum == 'planlandi'
    ).count()

    # Okunmamis bildirimler (kisiye ozel)
    okunmamis_bildirim = Bildirim.query.filter_by(
        kullanici_id=current_user.id,
        okundu=False
    ).count()

    # ========== GRAFIK VERISI: Son 6 ay gelir/gider/tahsilat ==========
    aylar_data = _son_n_ay_listesi(6)
    grafik_labels = []
    grafik_gelir = []
    grafik_gider = []
    grafik_tahsilat = []
    for yil, ay, ay_baslangic in aylar_data:
        grafik_labels.append(f'{AY_ADLARI[ay-1]} {str(yil)[-2:]}')
        g, gd = _ay_gelir_gider(ay_baslangic)
        grafik_gelir.append(g)
        grafik_gider.append(gd)

        # Ay sonu
        sonraki_ay = (ay_baslangic.replace(day=28) + timedelta(days=7)).replace(day=1)
        tah = db.session.query(
            func.coalesce(func.sum(Odeme.tutar), 0)
        ).filter(
            Odeme.iptal_edildi.is_(False),
            Odeme.tarih >= ay_baslangic,
            Odeme.tarih < sonraki_ay
        ).scalar() or 0
        grafik_tahsilat.append(float(tah))

    # ========== ON PLAN DUYURULAR ve ETKINLIKLER ==========
    # Sabitlenmis ve aktif duyurular (son 30 gun)
    son_duyurular = Duyuru.query.filter(
        Duyuru.aktif == True,  # noqa: E712
        Duyuru.yayinlanma_tarihi >= datetime.utcnow() - timedelta(days=30)
    ).order_by(
        Duyuru.sabitlenmis.desc(),
        Duyuru.yayinlanma_tarihi.desc()
    ).limit(5).all()

    # Yaklasan etkinlikler (gelecek 30 gun)
    try:
        yaklasan_etkinlikler = Etkinlik.query.filter(
            Etkinlik.baslangic_tarihi >= datetime.utcnow(),
            Etkinlik.baslangic_tarihi <= datetime.utcnow() + timedelta(days=30)
        ).order_by(Etkinlik.baslangic_tarihi.asc()).limit(5).all()
    except Exception:
        yaklasan_etkinlikler = []

    # ========== SON ISLEMLER ==========
    son_odemeler = Odeme.query.filter_by(iptal_edildi=False).order_by(
        Odeme.tarih.desc()
    ).limit(8).all()

    son_gelir_gider = GelirGiderKaydi.query.order_by(
        GelirGiderKaydi.tarih.desc(),
        GelirGiderKaydi.id.desc()
    ).limit(8).all()

    # Vadesi yaklasan taksitler (onumuzdeki 14 gun)
    yaklasan_taksitler = Taksit.query.filter(
        Taksit.durum.in_(['beklemede', 'kismi_odendi']),
        Taksit.vade_tarihi >= bugun,
        Taksit.vade_tarihi <= bugun + timedelta(days=14)
    ).join(OdemePlani).filter(OdemePlani.durum == 'aktif').order_by(
        Taksit.vade_tarihi.asc()
    ).limit(8).all()

    # Yaklasan personel izin donuslerı (bu hafta)
    bu_hafta_izindeki = PersonelIzin.query.filter(
        PersonelIzin.durum == 'onaylandi',
        PersonelIzin.baslangic_tarihi <= bugun + timedelta(days=7),
        PersonelIzin.bitis_tarihi >= bugun
    ).all()

    # Tenant abonelik plani + kullanim ozeti (sadece admin/yonetici icin gosterilir)
    tenant_kullanim = None
    if current_user.rol in ('admin', 'yonetici'):
        try:
            from app.tenancy.limitler import kullanim_durumu
            tenant_kullanim = kullanim_durumu()
        except Exception:
            tenant_kullanim = None

    return render_template(
        'main/dashboard.html',
        tenant_kullanim=tenant_kullanim,
        # Finansal KPI'lar
        aylik_gelir=aylik_gelir,
        aylik_gider=aylik_gider,
        aylik_kar=aylik_kar,
        aylik_tahsilat=aylik_tahsilat,
        geciken_taksitler=geciken_taksitler,
        geciken_tutar=geciken_tutar,
        toplam_bakiye=toplam_bakiye,
        yaklasan_taksit_sayi=yaklasan_taksit_sayi,
        # Kisi sayilari
        toplam_ogrenci=toplam_ogrenci,
        toplam_personel=toplam_personel,
        toplam_sinif=toplam_sinif,
        # Aktivite sayilari
        bugunku_devamsizlik=bugunku_devamsizlik,
        haftalik_devamsizlik=haftalik_devamsizlik,
        bekleyen_izin=bekleyen_izin,
        haftalik_gorusme=haftalik_gorusme,
        okunmamis_bildirim=okunmamis_bildirim,
        # Grafik
        grafik_labels=grafik_labels,
        grafik_gelir=grafik_gelir,
        grafik_gider=grafik_gider,
        grafik_tahsilat=grafik_tahsilat,
        # Listeler
        son_duyurular=son_duyurular,
        yaklasan_etkinlikler=yaklasan_etkinlikler,
        son_odemeler=son_odemeler,
        son_gelir_gider=son_gelir_gider,
        yaklasan_taksitler=yaklasan_taksitler,
        bu_hafta_izindeki=bu_hafta_izindeki,
        # Tarih
        bugun=bugun,
        simdi=datetime.now(),
    )
