from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from datetime import datetime
from app.models.rehberlik import Gorusme, OgrenciProfil, DavranisKaydi, VeliGorusmesi, RehberlikPlani
from app.rehberlik.risk_skoru import risk_listesi

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    now = datetime.utcnow()

    # Istatistikler
    toplam_gorusme = Gorusme.query.count()
    tamamlanan_gorusme = Gorusme.query.filter_by(durum='tamamlandi').count()
    planlanan_gorusme = Gorusme.query.filter_by(durum='planlandi').count()
    toplam_profil = OgrenciProfil.query.count()
    toplam_davranis = DavranisKaydi.query.count()
    olumlu_davranis = DavranisKaydi.query.filter_by(tur='olumlu').count()
    olumsuz_davranis = DavranisKaydi.query.filter_by(tur='olumsuz').count()
    toplam_veli = VeliGorusmesi.query.count()
    aktif_plan = RehberlikPlani.query.filter_by(durum='aktif').count()

    # Son gorusmeler
    son_gorusmeler = Gorusme.query.order_by(
        Gorusme.gorusme_tarihi.desc()
    ).limit(5).all()

    # Son davranis kayitlari
    son_davranislar = DavranisKaydi.query.order_by(
        DavranisKaydi.tarih.desc()
    ).limit(5).all()

    # Aktif planlar
    aktif_planlar = RehberlikPlani.query.filter_by(durum='aktif').order_by(
        RehberlikPlani.baslangic_tarihi.desc()
    ).limit(5).all()

    # Erken uyari: kompozit risk skoru (devamsizlik + deneme + davranis + profil)
    risk_ogrenciler = risk_listesi(limit=15, esik=30)
    risk_yuksek_sayi = sum(1 for r in risk_ogrenciler if r['seviye'] == 'yuksek')
    risk_orta_sayi = sum(1 for r in risk_ogrenciler if r['seviye'] == 'orta')

    return render_template('rehberlik/index.html',
                           risk_ogrenciler=risk_ogrenciler,
                           risk_yuksek_sayi=risk_yuksek_sayi,
                           risk_orta_sayi=risk_orta_sayi,
                           toplam_gorusme=toplam_gorusme,
                           tamamlanan_gorusme=tamamlanan_gorusme,
                           planlanan_gorusme=planlanan_gorusme,
                           toplam_profil=toplam_profil,
                           toplam_davranis=toplam_davranis,
                           olumlu_davranis=olumlu_davranis,
                           olumsuz_davranis=olumsuz_davranis,
                           toplam_veli=toplam_veli,
                           aktif_plan=aktif_plan,
                           son_gorusmeler=son_gorusmeler,
                           son_davranislar=son_davranislar,
                           aktif_planlar=aktif_planlar)
