from datetime import date, timedelta
from decimal import Decimal
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.muhasebe import (
    Ogrenci, OdemePlani, Taksit, Odeme, BankaHesabi
)
from app.muhasebe.forms import OdemePlaniForm, OdemeForm
from app.muhasebe.utils import makbuz_no_uret, banka_hareketi_olustur

bp = Blueprint('ogrenci_odeme', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'muhasebeci')
def liste():
    from app.muhasebe.utils import geciken_taksitleri_guncelle
    geciken_taksitleri_guncelle()

    page = request.args.get('page', 1, type=int)
    arama = request.args.get('q', '')

    query = Ogrenci.query.filter_by(aktif=True)
    if arama:
        query = query.filter(
            db.or_(
                Ogrenci.ad.ilike(f'%{arama}%'),
                Ogrenci.soyad.ilike(f'%{arama}%'),
                Ogrenci.ogrenci_no.ilike(f'%{arama}%')
            )
        )

    ogrenciler = query.order_by(Ogrenci.sinif, Ogrenci.soyad).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('muhasebe/ogrenci_odeme/liste.html',
                           ogrenciler=ogrenciler, arama=arama)



@bp.route('/<int:ogrenci_id>')
@login_required
@role_required('admin', 'muhasebeci')
def detay(ogrenci_id):
    from app.muhasebe.utils import geciken_taksitleri_guncelle
    geciken_taksitleri_guncelle()

    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    planlar = OdemePlani.query.filter_by(ogrenci_id=ogrenci_id).order_by(
        OdemePlani.olusturma_tarihi.desc()
    ).all()

    return render_template('muhasebe/ogrenci_odeme/detay.html',
                           ogrenci=ogrenci, planlar=planlar)


@bp.route('/<int:ogrenci_id>/plan-olustur', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci')
def plan_olustur(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    form = OdemePlaniForm()

    if form.validate_on_submit():
        indirim = Decimal(str(form.indirim_tutar.data or 0))
        toplam = Decimal(str(form.toplam_tutar.data))

        if indirim >= toplam:
            flash('İndirim tutarı toplam tutardan büyük veya eşit olamaz.', 'danger')
            return render_template('muhasebe/ogrenci_odeme/odeme_plani.html',
                                   form=form, ogrenci=ogrenci)

        plan = OdemePlani(
            ogrenci_id=ogrenci_id,
            donem=form.donem.data,
            toplam_tutar=form.toplam_tutar.data,
            indirim_tutar=indirim,
            indirim_aciklama=form.indirim_aciklama.data,
            taksit_sayisi=form.taksit_sayisi.data,
            aciklama=form.aciklama.data
        )
        db.session.add(plan)
        db.session.flush()

        # Taksitleri oluştur (indirim düşülmüş net tutar üzerinden)
        net_tutar = toplam - indirim
        taksit_tutari = net_tutar / form.taksit_sayisi.data
        kalan = net_tutar - (taksit_tutari * form.taksit_sayisi.data)

        bugun = date.today()
        for i in range(form.taksit_sayisi.data):
            tutar = taksit_tutari
            if i == form.taksit_sayisi.data - 1:
                tutar += kalan  # Son taksitte yuvarlama farkını ekle

            vade = bugun + timedelta(days=30 * (i + 1))
            taksit = Taksit(
                odeme_plani_id=plan.id,
                taksit_no=i + 1,
                tutar=tutar,
                vade_tarihi=vade,
                odenen_tutar=0,
                durum='beklemede'
            )
            db.session.add(taksit)

        db.session.commit()
        indirim_msg = f' (İndirim: {indirim:,.2f} ₺)' if indirim > 0 else ''
        flash(f'{form.taksit_sayisi.data} taksitli ödeme planı oluşturuldu.{indirim_msg}', 'success')
        return redirect(url_for('muhasebe.ogrenci_odeme.detay', ogrenci_id=ogrenci_id))

    return render_template('muhasebe/ogrenci_odeme/odeme_plani.html',
                           form=form, ogrenci=ogrenci)


@bp.route('/taksit/<int:taksit_id>/odeme', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci')
def odeme_yap(taksit_id):
    taksit = Taksit.query.get_or_404(taksit_id)
    ogrenci = taksit.odeme_plani.ogrenci
    form = OdemeForm()

    hesaplar = BankaHesabi.query.filter_by(aktif=True).all()
    form.banka_hesap_id.choices = [(0, '-- Seçiniz (Opsiyonel) --')] + \
        [(h.id, f'{h.banka_adi} - {h.hesap_adi}') for h in hesaplar]

    if form.validate_on_submit():
        odeme_tutari = Decimal(str(form.tutar.data))
        kalan = Decimal(str(taksit.tutar)) - Decimal(str(taksit.odenen_tutar))

        if odeme_tutari > kalan:
            flash(f'Ödeme tutarı kalan borçtan ({kalan:.2f} ₺) fazla olamaz.', 'danger')
            return render_template('muhasebe/ogrenci_odeme/odeme_yap.html',
                                   form=form, taksit=taksit, ogrenci=ogrenci)

        odeme = Odeme(
            taksit_id=taksit_id,
            tutar=form.tutar.data,
            odeme_turu=form.odeme_turu.data,
            banka_hesap_id=form.banka_hesap_id.data if form.banka_hesap_id.data else None,
            makbuz_no=makbuz_no_uret(),
            aciklama=form.aciklama.data,
            olusturan_id=current_user.id
        )
        db.session.add(odeme)

        # Taksit güncelle
        taksit.odenen_tutar = Decimal(str(taksit.odenen_tutar)) + odeme_tutari
        taksit.odeme_tarihi = date.today()
        taksit.durum_guncelle()

        # Banka hareketi
        if form.banka_hesap_id.data:
            banka_hareketi_olustur(
                form.banka_hesap_id.data, 'giris', form.tutar.data,
                aciklama=f'Öğrenci ödemesi: {ogrenci.tam_ad}'
            )

        db.session.commit()
        flash(f'Ödeme başarıyla kaydedildi. Makbuz No: {odeme.makbuz_no}', 'success')
        return redirect(url_for('muhasebe.ogrenci_odeme.makbuz', odeme_id=odeme.id))

    return render_template('muhasebe/ogrenci_odeme/odeme_yap.html',
                           form=form, taksit=taksit, ogrenci=ogrenci)


@bp.route('/odeme/<int:odeme_id>/makbuz')
@login_required
@role_required('admin', 'muhasebeci')
def makbuz(odeme_id):
    odeme = Odeme.query.get_or_404(odeme_id)
    ogrenci = odeme.taksit.odeme_plani.ogrenci
    return render_template('muhasebe/ogrenci_odeme/makbuz.html',
                           odeme=odeme, ogrenci=ogrenci)


@bp.route('/geciken')
@login_required
@role_required('admin', 'muhasebeci')
def geciken():
    from app.muhasebe.utils import geciken_taksitleri_guncelle
    geciken_taksitleri_guncelle()

    bugun = date.today()
    geciken_taksitler = Taksit.query.filter(
        Taksit.durum.in_(['beklemede', 'kismi_odendi', 'gecikti']),
        Taksit.vade_tarihi < bugun
    ).join(OdemePlani).join(Ogrenci).order_by(
        Taksit.vade_tarihi.asc()
    ).all()

    return render_template('muhasebe/ogrenci_odeme/geciken.html',
                           geciken_taksitler=geciken_taksitler)
