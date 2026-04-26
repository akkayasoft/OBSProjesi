from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required
from app.extensions import db
from app.models.rehberlik import OgrenciProfil, Gorusme, DavranisKaydi, VeliGorusmesi, RehberlikPlani
from app.models.muhasebe import Ogrenci
from app.rehberlik.forms import OgrenciProfilForm
from app.rehberlik.akademik_analiz import ogrenci_analizi
from app.rehberlik.risk_skoru import ogrenci_risk_skoru, risk_trend

bp = Blueprint('profil', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def liste():
    arama = request.args.get('arama', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Ogrenci.query.filter_by(aktif=True)

    if arama:
        query = query.filter(
            db.or_(
                Ogrenci.ad.ilike(f'%{arama}%'),
                Ogrenci.soyad.ilike(f'%{arama}%'),
                Ogrenci.ogrenci_no.ilike(f'%{arama}%')
            )
        )

    ogrenciler = query.order_by(Ogrenci.ad).paginate(page=page, per_page=20)

    return render_template('rehberlik/profil_listesi.html',
                           ogrenciler=ogrenciler,
                           arama=arama)


@bp.route('/<int:ogrenci_id>')
@login_required
@role_required('admin', 'ogretmen')
def ogrenci_profil(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    profil = OgrenciProfil.query.filter_by(ogrenci_id=ogrenci_id).first()

    gorusmeler = Gorusme.query.filter_by(ogrenci_id=ogrenci_id).order_by(
        Gorusme.gorusme_tarihi.desc()
    ).all()

    davranislar = DavranisKaydi.query.filter_by(ogrenci_id=ogrenci_id).order_by(
        DavranisKaydi.tarih.desc()
    ).all()

    veli_gorusmeleri = VeliGorusmesi.query.filter_by(ogrenci_id=ogrenci_id).order_by(
        VeliGorusmesi.gorusme_tarihi.desc()
    ).all()

    planlar = RehberlikPlani.query.filter_by(ogrenci_id=ogrenci_id).order_by(
        RehberlikPlani.baslangic_tarihi.desc()
    ).all()

    # Istatistikler
    olumlu_davranis = DavranisKaydi.query.filter_by(ogrenci_id=ogrenci_id, tur='olumlu').count()
    olumsuz_davranis = DavranisKaydi.query.filter_by(ogrenci_id=ogrenci_id, tur='olumsuz').count()

    # Deneme sinavi akademik analizi
    akademik = ogrenci_analizi(ogrenci_id)

    # Erken uyari: anlik risk skoru + 12 haftalik trend
    risk = ogrenci_risk_skoru(ogrenci_id)
    trend = risk_trend(ogrenci_id, hafta_sayisi=12)

    return render_template('rehberlik/ogrenci_profil.html',
                           ogrenci=ogrenci,
                           profil=profil,
                           gorusmeler=gorusmeler,
                           davranislar=davranislar,
                           veli_gorusmeleri=veli_gorusmeleri,
                           planlar=planlar,
                           olumlu_davranis=olumlu_davranis,
                           olumsuz_davranis=olumsuz_davranis,
                           akademik=akademik,
                           risk=risk,
                           risk_trend=trend)


@bp.route('/<int:ogrenci_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def profil_duzenle(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    profil = OgrenciProfil.query.filter_by(ogrenci_id=ogrenci_id).first()

    if profil:
        form = OgrenciProfilForm(obj=profil)
    else:
        form = OgrenciProfilForm()

    form.ogrenci_id.choices = [(ogrenci.id, f'{ogrenci.ogrenci_no} - {ogrenci.tam_ad}')]

    if form.validate_on_submit():
        if not profil:
            profil = OgrenciProfil(ogrenci_id=ogrenci_id)
            db.session.add(profil)

        profil.aile_durumu = form.aile_durumu.data
        profil.kardes_sayisi = form.kardes_sayisi.data
        profil.ekonomik_durum = form.ekonomik_durum.data
        profil.saglik_durumu = form.saglik_durumu.data
        profil.ozel_not = form.ozel_not.data
        profil.ilgi_alanlari = form.ilgi_alanlari.data
        profil.guclu_yonler = form.guclu_yonler.data
        profil.gelistirilecek_yonler = form.gelistirilecek_yonler.data

        db.session.commit()
        flash('Ogrenci profili basariyla guncellendi.', 'success')
        return redirect(url_for('rehberlik.profil.ogrenci_profil', ogrenci_id=ogrenci_id))

    if not profil:
        form.ogrenci_id.data = ogrenci_id

    return render_template('rehberlik/profil_form.html',
                           form=form, ogrenci=ogrenci,
                           baslik=f'{ogrenci.tam_ad} - Profil Duzenle')
