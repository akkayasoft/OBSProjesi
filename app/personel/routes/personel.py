from flask import (Blueprint, render_template, redirect, url_for, flash, request,
                   send_file)
from flask_login import login_required
from app.utils import role_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.muhasebe import Personel
from app.personel.forms import PersonelForm, PersonelDuzenleForm
from app.toplu_yukleme import (
    excel_sablonu_olustur, excel_oku,
    dogrula_str, dogrula_sayi, dogrula_tarih
)


PERSONEL_BASLIKLAR = [
    {'key': 'sicil_no', 'label': 'Sicil No', 'zorunlu': True},
    {'key': 'ad', 'label': 'Ad', 'zorunlu': True},
    {'key': 'soyad', 'label': 'Soyad', 'zorunlu': True},
    {'key': 'tc_kimlik', 'label': 'TC Kimlik'},
    {'key': 'cinsiyet', 'label': 'Cinsiyet (erkek/kadin)'},
    {'key': 'dogum_tarihi', 'label': 'Doğum Tarihi (YYYY-MM-DD)'},
    {'key': 'telefon', 'label': 'Telefon'},
    {'key': 'email', 'label': 'E-posta'},
    {'key': 'adres', 'label': 'Adres'},
    {'key': 'pozisyon', 'label': 'Pozisyon'},
    {'key': 'departman', 'label': 'Departman'},
    {'key': 'calisma_turu', 'label': 'Çalışma Türü (tam_zamanli/yari_zamanli/sozlesmeli)'},
    {'key': 'maas', 'label': 'Maaş'},
    {'key': 'ise_baslama_tarihi', 'label': 'İşe Başlama Tarihi (YYYY-MM-DD)'},
]


bp = Blueprint('personel_crud', __name__)


@bp.route('/')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def liste():
    arama = request.args.get('arama', '')
    departman = request.args.get('departman', '')
    durum = request.args.get('durum', '')
    page = request.args.get('page', 1, type=int)

    query = Personel.query

    if arama:
        query = query.filter(
            db.or_(
                Personel.ad.ilike(f'%{arama}%'),
                Personel.soyad.ilike(f'%{arama}%'),
                Personel.sicil_no.ilike(f'%{arama}%'),
            )
        )

    if departman:
        query = query.filter(Personel.departman == departman)

    if durum == 'aktif':
        query = query.filter(Personel.aktif == True)
    elif durum == 'pasif':
        query = query.filter(Personel.aktif == False)

    personeller = query.order_by(Personel.ad).paginate(page=page, per_page=20)

    return render_template('personel/personel/liste.html',
                           personeller=personeller,
                           arama=arama,
                           departman=departman,
                           durum=durum)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def yeni():
    form = PersonelForm()

    if form.validate_on_submit():
        mevcut = Personel.query.filter_by(sicil_no=form.sicil_no.data).first()
        if mevcut:
            flash('Bu sicil numarası zaten kayıtlı!', 'danger')
            return render_template('personel/personel/form.html', form=form, baslik='Yeni Personel')

        # Otomatik kullanıcı hesabı oluştur (username = sicil no)
        username = form.sicil_no.data
        varsayilan_sifre = form.tc_kimlik.data if form.tc_kimlik.data else form.sicil_no.data
        user = User(
            username=username,
            email=form.email.data or f"{username}@personel.obs",
            ad=form.ad.data,
            soyad=form.soyad.data,
            rol='ogretmen',
            aktif=True
        )
        user.set_password(varsayilan_sifre)
        db.session.add(user)
        db.session.flush()

        personel = Personel(
            user_id=user.id,
            sicil_no=form.sicil_no.data,
            tc_kimlik=form.tc_kimlik.data or None,
            ad=form.ad.data,
            soyad=form.soyad.data,
            cinsiyet=form.cinsiyet.data or None,
            dogum_tarihi=form.dogum_tarihi.data,
            telefon=form.telefon.data or None,
            email=form.email.data or None,
            adres=form.adres.data or None,
            pozisyon=form.pozisyon.data or None,
            departman=form.departman.data or None,
            calisma_turu=form.calisma_turu.data,
            maas=form.maas.data,
            ise_baslama_tarihi=form.ise_baslama_tarihi.data,
        )
        db.session.add(personel)
        db.session.commit()
        flash(f'{personel.tam_ad} başarıyla eklendi. '
              f'Giriş bilgileri — Kullanıcı adı: {username}, Şifre: {varsayilan_sifre}', 'success')
        return redirect(url_for('personel.personel_crud.detay', personel_id=personel.id))

    return render_template('personel/personel/form.html', form=form, baslik='Yeni Personel')


@bp.route('/<int:personel_id>')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def detay(personel_id):
    personel = Personel.query.get_or_404(personel_id)
    izinler = personel.izinler.order_by(db.desc('baslangic_tarihi')).all()
    odemeler = personel.odeme_kayitlari.order_by(db.desc('tarih')).limit(20).all()
    return render_template('personel/personel/detay.html',
                           personel=personel,
                           izinler=izinler,
                           odemeler=odemeler)


@bp.route('/<int:personel_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def duzenle(personel_id):
    personel = Personel.query.get_or_404(personel_id)
    form = PersonelDuzenleForm(obj=personel)

    if form.validate_on_submit():
        # Sicil no değiştiyse kontrol et
        if form.sicil_no.data != personel.sicil_no:
            mevcut = Personel.query.filter_by(sicil_no=form.sicil_no.data).first()
            if mevcut:
                flash('Bu sicil numarası zaten kayıtlı!', 'danger')
                return render_template('personel/personel/form.html',
                                       form=form, baslik='Personel Düzenle')

        personel.sicil_no = form.sicil_no.data
        personel.tc_kimlik = form.tc_kimlik.data or None
        personel.ad = form.ad.data
        personel.soyad = form.soyad.data
        personel.cinsiyet = form.cinsiyet.data or None
        personel.dogum_tarihi = form.dogum_tarihi.data
        personel.telefon = form.telefon.data or None
        personel.email = form.email.data or None
        personel.adres = form.adres.data or None
        personel.pozisyon = form.pozisyon.data or None
        personel.departman = form.departman.data or None
        personel.calisma_turu = form.calisma_turu.data
        personel.maas = form.maas.data
        personel.ise_baslama_tarihi = form.ise_baslama_tarihi.data
        personel.ise_bitis_tarihi = form.ise_bitis_tarihi.data

        # Bagli User hesabi varsa ad/soyad/email senkronize et
        senkronize_user = False
        if personel.user_id:
            user = User.query.get(personel.user_id)
            if user:
                user.ad = personel.ad
                user.soyad = personel.soyad
                if personel.email:
                    user.email = personel.email
                senkronize_user = True

        db.session.commit()
        msg = 'Personel bilgileri güncellendi.'
        if senkronize_user:
            msg += ' Sistem kullanıcısı da senkronize edildi.'
        flash(msg, 'success')
        return redirect(url_for('personel.personel_crud.detay', personel_id=personel.id))

    return render_template('personel/personel/form.html',
                           form=form, baslik='Personel Düzenle')


@bp.route('/<int:personel_id>/durum', methods=['POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def durum_degistir(personel_id):
    personel = Personel.query.get_or_404(personel_id)
    personel.aktif = not personel.aktif
    # Bagli kullaniciyi da pasiflestir/aktiflestir
    if personel.user_id:
        u = User.query.get(personel.user_id)
        if u:
            u.aktif = personel.aktif
    db.session.commit()
    durum_str = 'aktif' if personel.aktif else 'pasif'
    flash(f'{personel.tam_ad} {durum_str} yapıldı.', 'success')
    return redirect(url_for('personel.personel_crud.detay', personel_id=personel.id))


@bp.route('/<int:personel_id>/sil', methods=['POST'])
@login_required
@role_required('admin', 'yonetici')
def sil(personel_id):
    """Personel ve bagli sistem kullanicisini birlikte siler.

    Sicil/odeme/izin kayitlari personel.id uzerinden cascade ile temizlenir
    (modeldeki relationship'ler delete-orphan degil, ama lazy='dynamic';
    odeme_kayitlari ve izinler manuel silinmeli).
    """
    from app.models.muhasebe import PersonelOdemeKaydi
    from app.models.personel import PersonelIzin

    personel = Personel.query.get_or_404(personel_id)
    ad = personel.tam_ad
    user_id = personel.user_id

    # Bagli kayitlari sil
    PersonelIzin.query.filter_by(personel_id=personel.id).delete()
    PersonelOdemeKaydi.query.filter_by(personel_id=personel.id).delete()

    db.session.delete(personel)
    db.session.flush()

    # Bagli User'i da sil (sadece bu personel icin acilmissa — rol='ogretmen'
    # veya unique user_id ile baska personel referansi yoksa)
    silinen_user = False
    if user_id:
        user = User.query.get(user_id)
        if user and user.rol in ('ogretmen', 'muhasebeci'):
            db.session.delete(user)
            silinen_user = True

    db.session.commit()
    msg = f'"{ad}" personel kaydı silindi.'
    if silinen_user:
        msg += ' Sistem kullanıcısı da kaldırıldı.'
    flash(msg, 'success')
    return redirect(url_for('personel.personel_crud.liste'))


@bp.route('/<int:personel_id>/sifre-sifirla', methods=['POST'])
@login_required
@role_required('admin', 'yonetici')
def sifre_sifirla(personel_id):
    """Personelin sistem hesabinin sifresini sifirlar."""
    import secrets
    import string

    personel = Personel.query.get_or_404(personel_id)
    if not personel.user_id:
        flash(f'"{personel.tam_ad}" personelinin sistem hesabı bulunmuyor.',
              'warning')
        return redirect(url_for('personel.personel_crud.detay',
                                personel_id=personel.id))

    user = User.query.get(personel.user_id)
    if not user:
        flash('Bağlı sistem kullanıcısı bulunamadı.', 'danger')
        return redirect(url_for('personel.personel_crud.detay',
                                personel_id=personel.id))

    # Format: 'Pers' + 4 rakam + 2 buyuk harf
    rakamlar = ''.join(secrets.choice(string.digits) for _ in range(4))
    harfler = ''.join(secrets.choice(string.ascii_uppercase) for _ in range(2))
    yeni_sifre = f'Pers{rakamlar}{harfler}'

    user.set_password(yeni_sifre)
    db.session.commit()

    flash(
        f'🔑 "{personel.tam_ad}" personelinin şifresi sıfırlandı. '
        f'Kullanıcı adı: {user.username} · Yeni şifre: {yeni_sifre} — '
        f'lütfen kullanıcıya iletiniz '
        f'(bu mesaj kapatıldığında bir daha gösterilmez).',
        'sifre',
    )
    return redirect(url_for('personel.personel_crud.detay',
                            personel_id=personel.id))


@bp.route('/toplu-yukle/sablon')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def toplu_yukle_sablon():
    """Personel toplu yukleme Excel sablonunu indirir."""
    ornek = [
        ['P001', 'Ali', 'Kaya', '12345678901', 'erkek', '1985-03-12',
         '5321112233', 'ali@okul.com', 'Örnek Mah. 1 Sok.',
         'Matematik Öğretmeni', 'Matematik', 'tam_zamanli', '35000', '2020-09-01'],
        ['P002', 'Zeynep', 'Öz', '98765432109', 'kadin', '1990-07-25',
         '5322223344', 'zeynep@okul.com', '', 'Türkçe Öğretmeni',
         'Türkçe', 'yari_zamanli', '25000', '2022-02-15'],
    ]
    aciklama = ('Zorunlu alanlar kırmızı renkle işaretlidir. Çalışma türü: '
                '"tam_zamanli", "yari_zamanli" veya "sozlesmeli". Tarih formatı: YYYY-MM-DD.')
    output = excel_sablonu_olustur(PERSONEL_BASLIKLAR, ornek_satirlar=ornek,
                                    aciklama_satiri=aciklama, sayfa_adi='Personeller')
    return send_file(output, as_attachment=True,
                     download_name='personel_toplu_yukleme_sablonu.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@bp.route('/toplu-yukle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def toplu_yukle():
    """Excel dosyasi uzerinden personelleri toplu olusturur."""
    onizleme = None
    hatalar_ozet = None

    if request.method == 'POST':
        dosya = request.files.get('excel')
        islem = request.form.get('islem', 'onizle')

        if not dosya or not dosya.filename:
            flash('Lütfen bir Excel dosyası seçin.', 'danger')
            return render_template('personel/personel/toplu_yukle.html', onizleme=None)

        if not dosya.filename.lower().endswith(('.xlsx', '.xlsm')):
            flash('Sadece .xlsx formatında dosya yükleyebilirsiniz.', 'danger')
            return render_template('personel/personel/toplu_yukle.html', onizleme=None)

        try:
            satirlar = excel_oku(dosya, PERSONEL_BASLIKLAR)
        except Exception as exc:
            flash(f'Dosya okunamadı: {exc}', 'danger')
            return render_template('personel/personel/toplu_yukle.html', onizleme=None)

        mevcut_siciller = set(n for (n,) in db.session.query(Personel.sicil_no).all())
        dosya_siciller = set()
        gecerli_calisma_turleri = {'tam_zamanli', 'yari_zamanli', 'sozlesmeli'}

        for s in satirlar:
            sicil, err = dogrula_str(s.get('sicil_no'), zorunlu=True, max_len=20, label='Sicil No')
            if err:
                s['_hatalar'].append(err)
            else:
                s['sicil_no'] = sicil
                if sicil in mevcut_siciller:
                    s['_hatalar'].append(f'Sicil No "{sicil}" zaten kayıtlı.')
                if sicil in dosya_siciller:
                    s['_hatalar'].append(f'Sicil No "{sicil}" dosyada mükerrer.')
                dosya_siciller.add(sicil)

            ad, err = dogrula_str(s.get('ad'), zorunlu=True, max_len=100, label='Ad')
            if err:
                s['_hatalar'].append(err)
            else:
                s['ad'] = ad

            soyad, err = dogrula_str(s.get('soyad'), zorunlu=True, max_len=100, label='Soyad')
            if err:
                s['_hatalar'].append(err)
            else:
                s['soyad'] = soyad

            tc, err = dogrula_str(s.get('tc_kimlik'), max_len=11, label='TC Kimlik')
            if err:
                s['_hatalar'].append(err)
            else:
                s['tc_kimlik'] = tc

            cins, err = dogrula_str(s.get('cinsiyet'), max_len=10, label='Cinsiyet')
            if err:
                s['_hatalar'].append(err)
            elif cins and cins.lower() not in ('erkek', 'kadin'):
                s['_hatalar'].append('Cinsiyet "erkek" veya "kadin" olmalı.')
            else:
                s['cinsiyet'] = cins.lower() if cins else None

            dt, err = dogrula_tarih(s.get('dogum_tarihi'), label='Doğum Tarihi')
            if err:
                s['_hatalar'].append(err)
            else:
                s['dogum_tarihi'] = dt

            bt, err = dogrula_tarih(s.get('ise_baslama_tarihi'), label='İşe Başlama Tarihi')
            if err:
                s['_hatalar'].append(err)
            else:
                s['ise_baslama_tarihi'] = bt

            for key, lbl, mx in [('telefon', 'Telefon', 20), ('email', 'E-posta', 120),
                                 ('pozisyon', 'Pozisyon', 100), ('departman', 'Departman', 100)]:
                val, err = dogrula_str(s.get(key), max_len=mx, label=lbl)
                if err:
                    s['_hatalar'].append(err)
                else:
                    s[key] = val

            adres, err = dogrula_str(s.get('adres'), max_len=1000, label='Adres')
            if err:
                s['_hatalar'].append(err)
            else:
                s['adres'] = adres

            ct, err = dogrula_str(s.get('calisma_turu'), max_len=20, label='Çalışma Türü')
            if err:
                s['_hatalar'].append(err)
            elif ct and ct not in gecerli_calisma_turleri:
                s['_hatalar'].append('Çalışma Türü "tam_zamanli", "yari_zamanli" veya "sozlesmeli" olmalı.')
            else:
                s['calisma_turu'] = ct or 'tam_zamanli'

            maas, err = dogrula_sayi(s.get('maas'), min_val=0, label='Maaş')
            if err:
                s['_hatalar'].append(err)
            else:
                s['maas'] = maas

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
                    username = s['sicil_no']
                    varsayilan_sifre = s.get('tc_kimlik') or s['sicil_no']

                    if User.query.filter_by(username=username).first():
                        s['_hatalar'].append(f'Kullanıcı adı "{username}" zaten var.')
                        continue

                    user = User(
                        username=username,
                        email=s.get('email') or f"{username}@personel.obs",
                        ad=s['ad'],
                        soyad=s['soyad'],
                        rol='ogretmen',
                        aktif=True
                    )
                    user.set_password(varsayilan_sifre)
                    db.session.add(user)
                    db.session.flush()

                    personel = Personel(
                        user_id=user.id,
                        sicil_no=s['sicil_no'],
                        tc_kimlik=s.get('tc_kimlik'),
                        ad=s['ad'],
                        soyad=s['soyad'],
                        cinsiyet=s.get('cinsiyet'),
                        dogum_tarihi=s.get('dogum_tarihi'),
                        telefon=s.get('telefon'),
                        email=s.get('email'),
                        adres=s.get('adres'),
                        pozisyon=s.get('pozisyon'),
                        departman=s.get('departman'),
                        calisma_turu=s.get('calisma_turu') or 'tam_zamanli',
                        maas=s.get('maas'),
                        ise_baslama_tarihi=s.get('ise_baslama_tarihi'),
                        aktif=True,
                    )
                    db.session.add(personel)
                    eklenen += 1
                except Exception as exc:
                    db.session.rollback()
                    s['_hatalar'].append(f'Kayıt hatası: {exc}')

            db.session.commit()
            flash(f'{eklenen} personel başarıyla eklendi.' +
                  (f' {len(hatali)} satır hata nedeniyle atlandı.' if hatali else ''),
                  'success' if eklenen else 'warning')
            if not hatali:
                return redirect(url_for('personel.personel_crud.liste'))

        onizleme = satirlar

    return render_template('personel/personel/toplu_yukle.html',
                           onizleme=onizleme, hatalar_ozet=hatalar_ozet,
                           basliklar=PERSONEL_BASLIKLAR)
