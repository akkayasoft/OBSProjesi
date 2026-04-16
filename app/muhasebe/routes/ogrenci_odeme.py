from datetime import date, timedelta
from decimal import Decimal
from flask import (Blueprint, render_template, redirect, url_for, flash, request,
                   send_file)
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.muhasebe import (
    Ogrenci, OdemePlani, Taksit, Odeme, BankaHesabi
)
from app.muhasebe.forms import OdemePlaniForm, OdemeForm
from app.muhasebe.utils import makbuz_no_uret, banka_hareketi_olustur
from app.toplu_yukleme import (
    excel_sablonu_olustur, excel_oku,
    dogrula_str, dogrula_sayi, dogrula_tarih
)


ODEME_PLANI_BASLIKLAR = [
    {'key': 'ogrenci_no', 'label': 'Öğrenci No', 'zorunlu': True},
    {'key': 'donem', 'label': 'Dönem (ör. 2025-2026)', 'zorunlu': True},
    {'key': 'toplam_tutar', 'label': 'Toplam Tutar (₺)', 'zorunlu': True},
    {'key': 'indirim_tutar', 'label': 'İndirim Tutarı (₺)'},
    {'key': 'indirim_aciklama', 'label': 'İndirim Açıklaması'},
    {'key': 'taksit_sayisi', 'label': 'Taksit Sayısı', 'zorunlu': True},
    {'key': 'ilk_vade_tarihi', 'label': 'İlk Vade Tarihi (YYYY-MM-DD)'},
    {'key': 'aciklama', 'label': 'Açıklama'},
]


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


@bp.route('/toplu-plan/sablon')
@login_required
@role_required('admin', 'muhasebeci')
def toplu_plan_sablon():
    """Odeme plani toplu yukleme Excel sablonunu indirir."""
    ornek = [
        ['1001', '2025-2026', '24000', '2000', 'Kardeş indirimi', '8', '2025-10-01', 'Güz dönemi planı'],
        ['1002', '2025-2026', '22000', '0', '', '10', '', ''],
    ]
    aciklama = ('Zorunlu alanlar kırmızı renkle işaretlidir. '
                'İlk Vade Tarihi boş bırakılırsa bugünden 30 gün sonra ilk taksit başlar. '
                'Taksitler 30 günlük aralarla oluşturulur.')
    output = excel_sablonu_olustur(ODEME_PLANI_BASLIKLAR, ornek_satirlar=ornek,
                                    aciklama_satiri=aciklama, sayfa_adi='OdemePlanlari')
    return send_file(output, as_attachment=True,
                     download_name='odeme_plani_toplu_yukleme_sablonu.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@bp.route('/toplu-plan', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci')
def toplu_plan_yukle():
    """Excel dosyasi uzerinden ogrenci odeme planlarini toplu olusturur."""
    onizleme = None
    hatalar_ozet = None

    if request.method == 'POST':
        dosya = request.files.get('excel')
        islem = request.form.get('islem', 'onizle')

        if not dosya or not dosya.filename:
            flash('Lütfen bir Excel dosyası seçin.', 'danger')
            return render_template('muhasebe/ogrenci_odeme/toplu_plan_yukle.html', onizleme=None)

        if not dosya.filename.lower().endswith(('.xlsx', '.xlsm')):
            flash('Sadece .xlsx formatında dosya yükleyebilirsiniz.', 'danger')
            return render_template('muhasebe/ogrenci_odeme/toplu_plan_yukle.html', onizleme=None)

        try:
            satirlar = excel_oku(dosya, ODEME_PLANI_BASLIKLAR)
        except Exception as exc:
            flash(f'Dosya okunamadı: {exc}', 'danger')
            return render_template('muhasebe/ogrenci_odeme/toplu_plan_yukle.html', onizleme=None)

        # Dogrulama
        for s in satirlar:
            ogr_no, err = dogrula_str(s.get('ogrenci_no'), zorunlu=True, max_len=20, label='Öğrenci No')
            if err:
                s['_hatalar'].append(err)
                s['_ogrenci'] = None
            else:
                s['ogrenci_no'] = ogr_no
                ogrenci = Ogrenci.query.filter_by(ogrenci_no=ogr_no).first()
                if not ogrenci:
                    s['_hatalar'].append(f'Öğrenci No "{ogr_no}" sistemde bulunamadı.')
                    s['_ogrenci'] = None
                else:
                    s['_ogrenci'] = ogrenci
                    s['_ogrenci_ad'] = ogrenci.tam_ad

            donem, err = dogrula_str(s.get('donem'), zorunlu=True, max_len=20, label='Dönem')
            if err:
                s['_hatalar'].append(err)
            else:
                s['donem'] = donem

            toplam, err = dogrula_sayi(s.get('toplam_tutar'), zorunlu=True, min_val=1, label='Toplam Tutar')
            if err:
                s['_hatalar'].append(err)
            else:
                s['toplam_tutar'] = toplam

            indirim, err = dogrula_sayi(s.get('indirim_tutar'), min_val=0, label='İndirim Tutarı')
            if err:
                s['_hatalar'].append(err)
            else:
                s['indirim_tutar'] = indirim or Decimal('0')

            if s.get('toplam_tutar') is not None and s.get('indirim_tutar') is not None:
                if Decimal(str(s['indirim_tutar'])) >= Decimal(str(s['toplam_tutar'])):
                    s['_hatalar'].append('İndirim tutarı, toplam tutardan büyük veya eşit olamaz.')

            taksit_sayisi, err = dogrula_sayi(s.get('taksit_sayisi'), zorunlu=True,
                                              min_val=1, max_val=24, tam_sayi=True, label='Taksit Sayısı')
            if err:
                s['_hatalar'].append(err)
            else:
                s['taksit_sayisi'] = int(taksit_sayisi)

            ivt, err = dogrula_tarih(s.get('ilk_vade_tarihi'), label='İlk Vade Tarihi')
            if err:
                s['_hatalar'].append(err)
            else:
                s['ilk_vade_tarihi'] = ivt

            ind_acik, err = dogrula_str(s.get('indirim_aciklama'), max_len=200, label='İndirim Açıklaması')
            if err:
                s['_hatalar'].append(err)
            else:
                s['indirim_aciklama'] = ind_acik

            acik, err = dogrula_str(s.get('aciklama'), max_len=500, label='Açıklama')
            if err:
                s['_hatalar'].append(err)
            else:
                s['aciklama'] = acik

            # Ayni donemde aktif plan var mi?
            if s.get('_ogrenci') and s.get('donem'):
                mevcut = OdemePlani.query.filter_by(
                    ogrenci_id=s['_ogrenci'].id,
                    donem=s['donem'],
                    durum='aktif'
                ).first()
                if mevcut:
                    s['_hatalar'].append(f'{s["_ogrenci"].tam_ad} için {s["donem"]} döneminde aktif plan zaten var.')

        gecerli = [s for s in satirlar if not s['_hatalar']]
        hatali = [s for s in satirlar if s['_hatalar']]

        hatalar_ozet = {
            'toplam': len(satirlar),
            'gecerli': len(gecerli),
            'hatali': len(hatali),
        }

        if islem == 'kaydet' and gecerli:
            eklenen = 0
            for s in gecerli:
                try:
                    toplam = Decimal(str(s['toplam_tutar']))
                    indirim = Decimal(str(s.get('indirim_tutar') or 0))
                    taksit_sayisi = s['taksit_sayisi']

                    plan = OdemePlani(
                        ogrenci_id=s['_ogrenci'].id,
                        donem=s['donem'],
                        toplam_tutar=toplam,
                        indirim_tutar=indirim,
                        indirim_aciklama=s.get('indirim_aciklama'),
                        taksit_sayisi=taksit_sayisi,
                        aciklama=s.get('aciklama'),
                        durum='aktif'
                    )
                    db.session.add(plan)
                    db.session.flush()

                    net_tutar = toplam - indirim
                    taksit_tutari = net_tutar / taksit_sayisi
                    kalan = net_tutar - (taksit_tutari * taksit_sayisi)

                    ilk_vade = s.get('ilk_vade_tarihi') or (date.today() + timedelta(days=30))

                    for i in range(taksit_sayisi):
                        tutar = taksit_tutari
                        if i == taksit_sayisi - 1:
                            tutar += kalan

                        vade = ilk_vade + timedelta(days=30 * i)
                        taksit = Taksit(
                            odeme_plani_id=plan.id,
                            taksit_no=i + 1,
                            tutar=tutar,
                            vade_tarihi=vade,
                            odenen_tutar=0,
                            durum='beklemede'
                        )
                        db.session.add(taksit)

                    eklenen += 1
                except Exception as exc:
                    db.session.rollback()
                    s['_hatalar'].append(f'Plan oluşturma hatası: {exc}')

            db.session.commit()
            flash(f'{eklenen} ödeme planı başarıyla oluşturuldu.' +
                  (f' {len(hatali)} satır hata nedeniyle atlandı.' if hatali else ''),
                  'success' if eklenen else 'warning')
            if not hatali:
                return redirect(url_for('muhasebe.ogrenci_odeme.liste'))

        onizleme = satirlar

    return render_template('muhasebe/ogrenci_odeme/toplu_plan_yukle.html',
                           onizleme=onizleme, hatalar_ozet=hatalar_ozet,
                           basliklar=ODEME_PLANI_BASLIKLAR)


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
