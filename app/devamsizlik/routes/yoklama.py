from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.utils import role_required, current_user
from datetime import date

from app.extensions import db
from app.models.muhasebe import Ogrenci
from app.models.kayit import Sube, OgrenciKayit
from app.models.devamsizlik import Devamsizlik
from app.devamsizlik.forms import YoklamaSecimForm, TopluYoklamaSecimForm

bp = Blueprint('yoklama', __name__)


def _sube_choices():
    """Aktif şubeleri dropdown için döndürür."""
    subeler = Sube.query.filter_by(aktif=True).all()
    choices = [(0, '-- Sınıf / Şube Seçiniz --')]
    for s in subeler:
        choices.append((s.id, s.tam_ad))
    return choices


@bp.route('/')
@login_required
@role_required('admin', 'ogretmen')
def index():
    """Yoklama ana sayfası - sınıf ve tarih seçimi."""
    form = YoklamaSecimForm()
    form.sube_id.choices = _sube_choices()

    toplu_form = TopluYoklamaSecimForm()
    toplu_form.sube_id.choices = _sube_choices()

    return render_template('devamsizlik/yoklama/index.html',
                           form=form, toplu_form=toplu_form)


@bp.route('/al', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'ogretmen')
def yoklama_al():
    """Tek ders saati için yoklama al."""
    sube_id = request.args.get('sube_id', type=int) or request.form.get('sube_id', type=int)
    tarih_str = request.args.get('tarih') or request.form.get('tarih')
    ders_saati = request.args.get('ders_saati', type=int) or request.form.get('ders_saati', type=int)
    ders_saatleri = request.args.getlist('ders_saatleri', type=int) or request.form.getlist('ders_saatleri', type=int)

    if not ders_saati and len(ders_saatleri) == 1:
        ders_saati = ders_saatleri[0]

    if not sube_id or not tarih_str or not ders_saati:
        flash('Lütfen sınıf, tarih ve ders saati seçiniz.', 'warning')
        return redirect(url_for('devamsizlik.yoklama.index'))

    try:
        if isinstance(tarih_str, str):
            tarih = date.fromisoformat(tarih_str)
        else:
            tarih = tarih_str
    except ValueError:
        flash('Geçersiz tarih formatı.', 'danger')
        return redirect(url_for('devamsizlik.yoklama.index'))

    sube = Sube.query.get_or_404(sube_id)

    # Aktif öğrencileri getir
    aktif_kayitlar = OgrenciKayit.query.filter_by(
        sube_id=sube_id, durum='aktif'
    ).all()
    ogrenciler = [k.ogrenci for k in aktif_kayitlar]
    ogrenciler.sort(key=lambda o: (o.soyad, o.ad))

    # Mevcut devamsızlık kayıtlarını getir
    mevcut = {}
    for d in Devamsizlik.query.filter_by(sube_id=sube_id, tarih=tarih, ders_saati=ders_saati).all():
        mevcut[d.ogrenci_id] = d

    if request.method == 'POST' and 'kaydet' in request.form:
        # Mevcut kayıtları temizle
        Devamsizlik.query.filter_by(
            sube_id=sube_id, tarih=tarih, ders_saati=ders_saati
        ).delete()

        yeni_kayitlar = []
        kayit_sayisi = 0
        for ogrenci in ogrenciler:
            durum = request.form.get(f'durum_{ogrenci.id}')
            if durum and durum != 'mevcut':
                aciklama = request.form.get(f'aciklama_{ogrenci.id}', '').strip()
                d = Devamsizlik(
                    ogrenci_id=ogrenci.id,
                    sube_id=sube_id,
                    tarih=tarih,
                    ders_saati=ders_saati,
                    durum=durum,
                    aciklama=aciklama or None,
                    olusturan_id=current_user.id
                )
                db.session.add(d)
                yeni_kayitlar.append(d)
                kayit_sayisi += 1

        db.session.flush()  # ogrenci/sube relationship'leri canlansin

        # Otomatik bildirim — sadece YENI 'devamsiz' isaretleri icin
        from app.devamsizlik.bildirim import (
            devamsizlik_bildirimleri_gonder, yeni_devamsiz_kayitlari_filtrele,
        )
        bildirilecek = yeni_devamsiz_kayitlari_filtrele(yeni_kayitlar, mevcut)
        bildirim_sayisi = devamsizlik_bildirimleri_gonder(bildirilecek)

        db.session.commit()
        ek = (f' {bildirim_sayisi} bildirim gönderildi.'
              if bildirim_sayisi else '')
        flash(f'{sube.tam_ad} - {ders_saati}. ders yoklaması kaydedildi. '
              f'{kayit_sayisi} devamsızlık kaydı oluşturuldu.{ek}',
              'success')
        return redirect(url_for('devamsizlik.yoklama.index'))

    return render_template('devamsizlik/yoklama/yoklama_al.html',
                           sube=sube, tarih=tarih, ders_saati=ders_saati,
                           ogrenciler=ogrenciler, mevcut=mevcut)


@bp.route('/toplu', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def toplu_yoklama():
    """Birden fazla ders saati için yoklama yönlendirme."""
    sube_id = request.form.get('sube_id', type=int)
    tarih = request.form.get('tarih')
    ders_saatleri = request.form.getlist('ders_saatleri', type=int)

    if not sube_id or not tarih or not ders_saatleri:
        flash('Lütfen tüm alanları doldurunuz.', 'warning')
        return redirect(url_for('devamsizlik.yoklama.index'))

    sube = Sube.query.get_or_404(sube_id)

    # Aktif öğrencileri getir
    aktif_kayitlar = OgrenciKayit.query.filter_by(
        sube_id=sube_id, durum='aktif'
    ).all()
    ogrenciler = [k.ogrenci for k in aktif_kayitlar]
    ogrenciler.sort(key=lambda o: (o.soyad, o.ad))

    try:
        tarih_obj = date.fromisoformat(tarih)
    except ValueError:
        flash('Geçersiz tarih formatı.', 'danger')
        return redirect(url_for('devamsizlik.yoklama.index'))

    # Mevcut kayıtları getir
    mevcut = {}
    for ds in ders_saatleri:
        mevcut[ds] = {}
        for d in Devamsizlik.query.filter_by(sube_id=sube_id, tarih=tarih_obj, ders_saati=ds).all():
            mevcut[ds][d.ogrenci_id] = d

    return render_template('devamsizlik/yoklama/toplu_yoklama.html',
                           sube=sube, tarih=tarih_obj, ders_saatleri=ders_saatleri,
                           ogrenciler=ogrenciler, mevcut=mevcut)


@bp.route('/toplu/kaydet', methods=['POST'])
@login_required
@role_required('admin', 'ogretmen')
def toplu_yoklama_kaydet():
    """Toplu yoklama kaydet."""
    sube_id = request.form.get('sube_id', type=int)
    tarih_str = request.form.get('tarih')
    ders_saatleri = request.form.getlist('ders_saatleri', type=int)

    if not sube_id or not tarih_str or not ders_saatleri:
        flash('Geçersiz istek.', 'danger')
        return redirect(url_for('devamsizlik.yoklama.index'))

    try:
        tarih = date.fromisoformat(tarih_str)
    except ValueError:
        flash('Geçersiz tarih formatı.', 'danger')
        return redirect(url_for('devamsizlik.yoklama.index'))
    sube = Sube.query.get_or_404(sube_id)

    aktif_kayitlar = OgrenciKayit.query.filter_by(
        sube_id=sube_id, durum='aktif'
    ).all()
    ogrenciler = [k.ogrenci for k in aktif_kayitlar]

    # Onceki devamsizlik kayitlarini topla — bildirim spam'ini onlemek icin
    # ayni ders saatinde zaten 'devamsiz' isaretliydiyse atlayacagiz
    onceki = {}  # (ders_saati, ogrenci_id) -> Devamsizlik
    for d in Devamsizlik.query.filter_by(sube_id=sube_id, tarih=tarih).filter(
            Devamsizlik.ders_saati.in_(ders_saatleri)).all():
        onceki[(d.ders_saati, d.ogrenci_id)] = d

    yeni_kayitlar = []
    toplam_kayit = 0
    for ds in ders_saatleri:
        # Mevcut kayıtları temizle
        Devamsizlik.query.filter_by(
            sube_id=sube_id, tarih=tarih, ders_saati=ds
        ).delete()

        for ogrenci in ogrenciler:
            durum = request.form.get(f'durum_{ds}_{ogrenci.id}')
            if durum and durum != 'mevcut':
                aciklama = request.form.get(f'aciklama_{ds}_{ogrenci.id}', '').strip()
                d = Devamsizlik(
                    ogrenci_id=ogrenci.id,
                    sube_id=sube_id,
                    tarih=tarih,
                    ders_saati=ds,
                    durum=durum,
                    aciklama=aciklama or None,
                    olusturan_id=current_user.id
                )
                db.session.add(d)
                yeni_kayitlar.append(d)
                toplam_kayit += 1

    db.session.flush()

    # Otomatik bildirim — sadece YENI 'devamsiz' isaretleri icin (spam'i onle)
    from app.devamsizlik.bildirim import devamsizlik_bildirimleri_gonder
    bildirilecek = []
    for k in yeni_kayitlar:
        if k.durum != 'devamsiz':
            continue
        eski = onceki.get((k.ders_saati, k.ogrenci_id))
        if eski is not None and eski.durum == 'devamsiz':
            continue
        bildirilecek.append(k)
    bildirim_sayisi = devamsizlik_bildirimleri_gonder(bildirilecek)

    db.session.commit()
    ek = (f' {bildirim_sayisi} bildirim gönderildi.' if bildirim_sayisi else '')
    flash(f'{sube.tam_ad} - {len(ders_saatleri)} ders saati yoklaması kaydedildi. '
          f'{toplam_kayit} devamsızlık kaydı oluşturuldu.{ek}', 'success')
    return redirect(url_for('devamsizlik.yoklama.index'))


@bp.route('/ogrenci/<int:ogrenci_id>')
@login_required
@role_required('admin', 'ogretmen')
def ogrenci_devamsizlik(ogrenci_id):
    """Bir öğrencinin devamsızlık detayları."""
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)

    kayitlar = Devamsizlik.query.filter_by(ogrenci_id=ogrenci_id)\
        .order_by(Devamsizlik.tarih.desc(), Devamsizlik.ders_saati).all()

    # İstatistikler
    toplam = len(kayitlar)
    devamsiz = sum(1 for k in kayitlar if k.durum == 'devamsiz')
    gec = sum(1 for k in kayitlar if k.durum == 'gec')
    izinli = sum(1 for k in kayitlar if k.durum == 'izinli')
    raporlu = sum(1 for k in kayitlar if k.durum == 'raporlu')

    # Günlük bazda devamsızlık (özetsiz gün sayısı)
    gunler = set(k.tarih for k in kayitlar if k.durum == 'devamsiz')
    devamsiz_gun = len(gunler)

    istatistik = {
        'toplam': toplam,
        'devamsiz': devamsiz,
        'gec': gec,
        'izinli': izinli,
        'raporlu': raporlu,
        'devamsiz_gun': devamsiz_gun,
    }

    return render_template('devamsizlik/yoklama/ogrenci_detay.html',
                           ogrenci=ogrenci, kayitlar=kayitlar,
                           istatistik=istatistik)
