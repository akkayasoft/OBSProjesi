import base64
import json
import os
import re
import uuid
from datetime import date, datetime
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, session, send_from_directory, abort,
                   send_file)
from flask_login import login_required
from werkzeug.utils import secure_filename
from app.utils import role_required, current_user
from app.extensions import db
from app.models.user import User
from app.models.muhasebe import Ogrenci
from app.models.kayit import (
    Sinif, Sube, KayitDonemi, OgrenciKayit, VeliBilgisi, OgrenciBelge
)
from app.kayit.forms import (
    OgrenciKayitForm, OgrenciDuzenleForm, DurumDegistirForm, VeliForm,
    KarteksYukleForm
)
from app.toplu_yukleme import (
    excel_sablonu_olustur, excel_oku,
    dogrula_str, dogrula_sayi, dogrula_tarih
)


OGRENCI_BASLIKLAR = [
    {'key': 'ogrenci_no', 'label': 'Öğrenci No', 'zorunlu': True},
    {'key': 'ad', 'label': 'Ad', 'zorunlu': True},
    {'key': 'soyad', 'label': 'Soyad', 'zorunlu': True},
    {'key': 'tc_kimlik', 'label': 'TC Kimlik'},
    {'key': 'cinsiyet', 'label': 'Cinsiyet (erkek/kadin)'},
    {'key': 'dogum_tarihi', 'label': 'Doğum Tarihi (YYYY-MM-DD)'},
    {'key': 'donem_ad', 'label': 'Eğitim-Öğretim Yılı'},
    {'key': 'sinif_ad', 'label': 'Sınıf'},
    {'key': 'sube_ad', 'label': 'Şube'},
    {'key': 'telefon', 'label': 'Telefon'},
    {'key': 'email', 'label': 'E-posta'},
    {'key': 'adres', 'label': 'Adres'},
    {'key': 'veli_ad', 'label': 'Veli Ad Soyad'},
    {'key': 'veli_telefon', 'label': 'Veli Telefon'},
]


def _seviye_from_ad(ad: str) -> int:
    """'9. Sınıf' -> 9, 'TYT' -> 13, 'AYT' -> 14, diger -> 0."""
    if not ad:
        return 0
    m = re.search(r'(\d+)', ad)
    if m:
        try:
            n = int(m.group(1))
            if 1 <= n <= 12:
                return n
        except ValueError:
            pass
    u = ad.strip().upper()
    if 'TYT' in u:
        return 13
    if 'AYT' in u:
        return 14
    return 0


def _parse_donem_tarihleri(ad: str):
    """'2025-2026' -> (2025-09-01, 2026-06-30). Bulunamazsa bugünden +1 yil."""
    m = re.search(r'(20\d{2})\s*[-/]\s*(20\d{2})', str(ad or ''))
    if m:
        y1 = int(m.group(1))
        y2 = int(m.group(2))
        return date(y1, 9, 1), date(y2, 6, 30)
    # Tek yil yazilmis olabilir
    m1 = re.search(r'(20\d{2})', str(ad or ''))
    if m1:
        y1 = int(m1.group(1))
        return date(y1, 9, 1), date(y1 + 1, 6, 30)
    today = date.today()
    return today, date(today.year + 1, today.month, today.day)


def resolve_or_create_donem(ad: str) -> 'KayitDonemi':
    """Isme göre KayitDonemi bulur veya olusturur. `ad` bos ise None."""
    if not ad:
        return None
    ad = ad.strip()
    donem = KayitDonemi.query.filter(db.func.lower(KayitDonemi.ad) == ad.lower()).first()
    if donem:
        return donem
    bas, bit = _parse_donem_tarihleri(ad)
    donem = KayitDonemi(ad=ad, baslangic_tarihi=bas, bitis_tarihi=bit, aktif=True)
    db.session.add(donem)
    db.session.flush()
    return donem


def resolve_or_create_sinif(ad: str) -> 'Sinif':
    """Isme göre Sinif bulur veya olusturur. `ad` bos ise None."""
    if not ad:
        return None
    ad = ad.strip()
    sinif = Sinif.query.filter(db.func.lower(Sinif.ad) == ad.lower()).first()
    if sinif:
        return sinif
    seviye = _seviye_from_ad(ad)
    sinif = Sinif(ad=ad, seviye=seviye, aktif=True)
    db.session.add(sinif)
    db.session.flush()
    return sinif


def resolve_or_create_sube(sinif: 'Sinif', ad: str, kontenjan: int = 30) -> 'Sube':
    """Verilen sinifin altinda Sube bulur veya olusturur. `ad` veya sinif bos ise None."""
    if not sinif or not ad:
        return None
    ad = ad.strip()
    sube = Sube.query.filter(
        Sube.sinif_id == sinif.id,
        db.func.lower(Sube.ad) == ad.lower()
    ).first()
    if sube:
        return sube
    sube = Sube(sinif_id=sinif.id, ad=ad, kontenjan=kontenjan, aktif=True)
    db.session.add(sube)
    db.session.flush()
    return sube

bp = Blueprint('ogrenci', __name__)


def _save_belge_dosyasi(file_storage, alt_klasor: str) -> tuple[str, str]:
    """
    Yüklenen dosyayı `instance/uploads/<alt_klasor>/` altına kaydeder.
    Geri dönüş: (relative_path, original_filename).
    """
    klasor = os.path.join(current_app.config['UPLOAD_FOLDER'], alt_klasor)
    os.makedirs(klasor, exist_ok=True)

    orijinal = secure_filename(file_storage.filename or 'belge')
    uzanti = os.path.splitext(orijinal)[1].lower() or '.bin'
    yeni_ad = f"{uuid.uuid4().hex}{uzanti}"
    tam_yol = os.path.join(klasor, yeni_ad)
    file_storage.save(tam_yol)

    # DB'ye `instance/uploads/` köküne göre relative path kaydedelim
    rel = os.path.join(alt_klasor, yeni_ad)
    return rel, orijinal


@bp.route('/')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def liste():
    page = request.args.get('page', 1, type=int)
    arama = request.args.get('q', '')
    sinif_filtre = request.args.get('sinif', 0, type=int)
    durum_filtre = request.args.get('durum', '')

    query = Ogrenci.query.filter_by(aktif=True)
    kayit_joined = False

    if arama:
        query = query.filter(
            db.or_(
                Ogrenci.ad.ilike(f'%{arama}%'),
                Ogrenci.soyad.ilike(f'%{arama}%'),
                Ogrenci.ogrenci_no.ilike(f'%{arama}%'),
                Ogrenci.tc_kimlik.ilike(f'%{arama}%')
            )
        )

    if sinif_filtre:
        if not kayit_joined:
            query = query.join(OgrenciKayit)
            kayit_joined = True
        query = query.join(Sube).filter(
            Sube.sinif_id == sinif_filtre,
            OgrenciKayit.durum == 'aktif'
        )

    if durum_filtre:
        if not kayit_joined:
            query = query.join(OgrenciKayit)
            kayit_joined = True
        query = query.filter(OgrenciKayit.durum == durum_filtre)

    if kayit_joined:
        query = query.distinct()

    ogrenciler = query.order_by(Ogrenci.soyad, Ogrenci.ad).paginate(
        page=page, per_page=20, error_out=False
    )

    siniflar = Sinif.query.filter_by(aktif=True).order_by(Sinif.seviye).all()

    return render_template('kayit/ogrenci/liste.html',
                           ogrenciler=ogrenciler,
                           siniflar=siniflar,
                           arama=arama,
                           sinif_filtre=sinif_filtre,
                           durum_filtre=durum_filtre)


@bp.route('/toplu-yukle/sablon')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def toplu_yukle_sablon():
    """Ogrenci toplu yukleme Excel sablonunu indirir."""
    ornek = [
        ['1001', 'Ahmet', 'Yılmaz', '12345678901', 'erkek', '2010-05-15',
         '2025-2026', '9. Sınıf', 'A', '5321234567', 'ahmet@example.com',
         'Örnek Mah. 1 Sok.', 'Mehmet Yılmaz', '5329876543'],
        ['1002', 'Ayşe', 'Demir', '10987654321', 'kadin', '2011-08-22',
         '2025-2026', 'TYT', 'A', '5321234568', '', '',
         'Fatma Demir', '5329876544'],
    ]
    aciklama = ('Zorunlu alanlar kırmızı renkle işaretlidir. Cinsiyet alanına ' +
                '"erkek" veya "kadin" yazın. Tarih formatı: YYYY-MM-DD. ' +
                'Eğitim-Öğretim Yılı / Sınıf / Şube boş bırakılırsa form üstünden ' +
                'seçilen varsayılan değerler kullanılır; yazılırsa otomatik oluşturulur.')
    output = excel_sablonu_olustur(OGRENCI_BASLIKLAR, ornek_satirlar=ornek,
                                    aciklama_satiri=aciklama, sayfa_adi='Ogrenciler')
    return send_file(output, as_attachment=True,
                     download_name='ogrenci_toplu_yukleme_sablonu.xlsx',
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def _toplu_dogrula(satirlar, varsayilan_donem, varsayilan_sube):
    """Excel'den okunan ham satirlari dogrular, '_hatalar' listesini doldurur.

    satirlar listesini yerinde modifiye eder. Geri donerken ayni listeyi verir.
    """
    mevcut_numaralar = set(n for (n,) in db.session.query(Ogrenci.ogrenci_no).all())
    # User.email UNIQUE oldugu icin email catismalarini validation fazinda yakala.
    mevcut_emailler = set(e.lower() for (e,) in db.session.query(User.email).all() if e)
    mevcut_usernames = set(u.lower() for (u,) in db.session.query(User.username).all() if u)
    dosya_numaralar = set()
    dosya_emailler = set()

    for s in satirlar:
        ogr_no, err = dogrula_str(s.get('ogrenci_no'), zorunlu=True, max_len=20, label='Öğrenci No')
        if err:
            s['_hatalar'].append(err)
        else:
            s['ogrenci_no'] = ogr_no
            if ogr_no in mevcut_numaralar:
                s['_hatalar'].append(f'Öğrenci No "{ogr_no}" zaten kayıtlı.')
            if ogr_no in dosya_numaralar:
                s['_hatalar'].append(f'Öğrenci No "{ogr_no}" dosyada mükerrer.')
            # Ogrenci no ayni zamanda username olacak — User.username UNIQUE
            if ogr_no.lower() in mevcut_usernames:
                s['_hatalar'].append(
                    f'Öğrenci No "{ogr_no}" başka bir kullanıcı adıyla çakışıyor.')
            dosya_numaralar.add(ogr_no)

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

        for key, lbl, mx in [('telefon', 'Telefon', 20),
                             ('email', 'E-posta', 120), ('veli_ad', 'Veli Ad', 100),
                             ('veli_telefon', 'Veli Telefon', 20)]:
            val, err = dogrula_str(s.get(key), max_len=mx, label=lbl)
            if err:
                s['_hatalar'].append(err)
            else:
                s[key] = val

        # E-posta mukerrer kontrolu: hem DB'de hem dosyada. Otomatik atanacak
        # "{ogrenci_no}@ogrenci.obs" email'ini atla (zaten ogrenci_no unique).
        eposta = s.get('email')
        if eposta:
            e_low = eposta.lower()
            if e_low in mevcut_emailler:
                s['_hatalar'].append(
                    f'E-posta "{eposta}" zaten başka bir kullanıcıda kayıtlı.')
            if e_low in dosya_emailler:
                s['_hatalar'].append(
                    f'E-posta "{eposta}" dosyada mükerrer.')
            dosya_emailler.add(e_low)

        adres, err = dogrula_str(s.get('adres'), max_len=1000, label='Adres')
        if err:
            s['_hatalar'].append(err)
        else:
            s['adres'] = adres

        # --- Donem / Sinif / Sube cozumleme ---
        donem_ad, err = dogrula_str(s.get('donem_ad'), max_len=20, label='Eğitim-Öğretim Yılı')
        if err:
            s['_hatalar'].append(err)
        sinif_ad, err = dogrula_str(s.get('sinif_ad'), max_len=50, label='Sınıf')
        if err:
            s['_hatalar'].append(err)
        sube_ad, err = dogrula_str(s.get('sube_ad'), max_len=10, label='Şube')
        if err:
            s['_hatalar'].append(err)

        # Kullanici "7-A", "7/A", "7 A", "7A" gibi SINIF+SUBE'yi birlesik yazmis olabilir.
        # Sube bos ise ve sinif bu paterni iceriyorsa otomatik ayir.
        if sinif_ad and not sube_ad:
            m = re.match(r'^\s*(\d{1,2})\s*[-/\.\s]+\s*([A-Za-zÇĞİÖŞÜçğıöşü]{1,5})\s*$',
                         sinif_ad)
            if not m:
                # "7A", "12B" bitişik formu
                m = re.match(r'^\s*(\d{1,2})([A-Za-zÇĞİÖŞÜçğıöşü]{1,5})\s*$',
                             sinif_ad)
            if m:
                n = m.group(1)
                sb = m.group(2).upper()
                sinif_ad = f'{n}. Sınıf'
                sube_ad = sb

        # Etkin donem: satirdaki ad varsa o, yoksa formdaki varsayilan
        if donem_ad:
            s['_donem_ad'] = donem_ad
        elif varsayilan_donem:
            s['_donem_ad'] = varsayilan_donem.ad
        else:
            s['_hatalar'].append(
                'Eğitim-Öğretim Yılı boş. Üstteki "Varsayılan Kayıt Dönemi" '
                'dropdown\'undan seçim yapın ya da Excel\'de ilgili sütunu doldurun.'
            )

        # Etkin sinif: satirda varsa o, yoksa varsayilan_sube.sinif.ad
        if sinif_ad:
            s['_sinif_ad'] = sinif_ad
        elif varsayilan_sube:
            s['_sinif_ad'] = varsayilan_sube.sinif.ad
        else:
            s['_hatalar'].append(
                'Sınıf boş. Üstteki "Varsayılan Şube" dropdown\'undan seçim yapın '
                'ya da Excel\'de Sınıf sütununu doldurun (ör. "7. Sınıf" veya "7-A").'
            )

        # Etkin sube: satirda sube_ad varsa o, yoksa varsayilan
        if sube_ad:
            s['_sube_ad'] = sube_ad
        elif varsayilan_sube:
            s['_sube_ad'] = varsayilan_sube.ad
        else:
            s['_hatalar'].append(
                'Şube boş. Excel\'de "Şube" sütununa A/B/C yazın veya Sınıf sütununda '
                '"7-A" gibi birleşik yazın; ya da üstten varsayılan Şube seçin.'
            )

        # Ogrenci.sinif string alani icin
        if s.get('_sinif_ad'):
            s['sinif'] = s['_sinif_ad']

    return satirlar


def _satir_to_jsonable(satirlar):
    """Dogrulanmis satirlari JSON'a cevrilebilir hale getirir.
    date/datetime -> ISO string, Decimal -> str, set -> list.
    """
    out = []
    for s in satirlar:
        d = {}
        for k, v in s.items():
            if isinstance(v, (date, datetime)):
                d[k] = v.isoformat()
            elif v is None:
                d[k] = None
            else:
                d[k] = v if isinstance(v, (str, int, float, bool, list, dict)) else str(v)
        out.append(d)
    return out


def _jsonable_to_satir(satirlar):
    """_satir_to_jsonable'in tersi: ISO tarih stringlerini date'e cevir."""
    out = []
    for s in satirlar:
        d = dict(s)
        # dogum_tarihi string geldiyse date'e cevir
        dt_str = d.get('dogum_tarihi')
        if isinstance(dt_str, str) and dt_str:
            try:
                d['dogum_tarihi'] = datetime.fromisoformat(dt_str).date()
            except ValueError:
                d['dogum_tarihi'] = None
        # _hatalar listesinin var oldugundan emin ol
        d.setdefault('_hatalar', [])
        out.append(d)
    return out


def _encode_payload(satirlar):
    """Satir listesini base64 encoded JSON string'e cevir (hidden input icin)."""
    raw = json.dumps(_satir_to_jsonable(satirlar), ensure_ascii=False).encode('utf-8')
    return base64.b64encode(raw).decode('ascii')


def _decode_payload(s):
    """base64 encoded JSON'i satir listesine cevir."""
    if not s:
        return []
    try:
        raw = base64.b64decode(s.encode('ascii'))
        data = json.loads(raw.decode('utf-8'))
        return _jsonable_to_satir(data)
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return []


def _satir_to_display(satirlar):
    """Template'e gondermeden once date/datetime degerlerini ISO string'e cevir.
    Inputlarda `value="2010-03-14"` gibi yazilabilsin diye.
    """
    for s in satirlar:
        for k, v in list(s.items()):
            if isinstance(v, (date, datetime)):
                s[k] = v.isoformat()
    return satirlar


def _form_alanlarindan_satirlar(form):
    """request.form'dan 'row_<satir_no>_<key>' alanlarini toplar.

    Kullanicinin inline duzenlediği preview tablosundan gelen satirlari
    reconstruct eder. Key'ler underscore icerebilir (ogrenci_no, veli_ad...)
    oldugu icin once '<sayilar>_' onekini cikarip geri kalani key kabul eder.
    """
    satirlar_map = {}
    for field_name, value in form.items():
        m = re.match(r'^row_(\d+)_(.+)$', field_name)
        if not m:
            continue
        satir_no = int(m.group(1))
        key = m.group(2)
        if isinstance(value, str):
            value = value.strip()
        d = satirlar_map.setdefault(
            satir_no, {'_satir_no': satir_no, '_hatalar': []})
        d[key] = value if value else None
    return [satirlar_map[k] for k in sorted(satirlar_map.keys())]


def _ogrenci_kaydet_bir(s):
    """Tek bir gecerli satiri DB'ye yazar. Basarili ise (True, None),
    aksi halde (False, 'hata mesaji') doner. Basarisizlikta rollback yapar."""
    from sqlalchemy.exc import IntegrityError
    try:
        username = s['ogrenci_no']
        varsayilan_sifre = s.get('tc_kimlik') or s['ogrenci_no']
        email = s.get('email') or f"{username}@ogrenci.obs"

        # DB seviyesindeki UNIQUE constraint'leri onceden kontrol et — boylece
        # psycopg2.errors.UniqueViolation ham SQL hatasi kullaniciya yansimaz.
        if User.query.filter_by(username=username).first():
            return False, f"Kullanıcı adı '{username}' zaten var."
        if Ogrenci.query.filter_by(ogrenci_no=s['ogrenci_no']).first():
            return False, f"Öğrenci No '{s['ogrenci_no']}' zaten kayıtlı."
        if User.query.filter(db.func.lower(User.email) == email.lower()).first():
            return False, f"E-posta '{email}' zaten başka bir kullanıcıda kayıtlı."

        donem = resolve_or_create_donem(s.get('_donem_ad'))
        sinif = resolve_or_create_sinif(s.get('_sinif_ad'))
        sube = resolve_or_create_sube(sinif, s.get('_sube_ad'))

        if not donem or not sube:
            return False, 'Dönem/Sınıf/Şube çözümlenemedi.'

        user = User(
            username=username,
            email=email,
            ad=s['ad'],
            soyad=s['soyad'],
            rol='ogrenci',
            aktif=True,
        )
        user.set_password(varsayilan_sifre)
        db.session.add(user)
        db.session.flush()

        ogrenci = Ogrenci(
            user_id=user.id,
            ogrenci_no=s['ogrenci_no'],
            tc_kimlik=s.get('tc_kimlik'),
            ad=s['ad'],
            soyad=s['soyad'],
            cinsiyet=s.get('cinsiyet'),
            dogum_tarihi=s.get('dogum_tarihi'),
            sinif=s.get('sinif') or sube.sinif.ad,
            telefon=s.get('telefon'),
            email=s.get('email'),
            adres=s.get('adres'),
            veli_ad=s.get('veli_ad'),
            veli_telefon=s.get('veli_telefon'),
            aktif=True,
        )
        db.session.add(ogrenci)
        db.session.flush()

        kayit = OgrenciKayit(
            ogrenci_id=ogrenci.id,
            donem_id=donem.id,
            sube_id=sube.id,
            kayit_tarihi=date.today(),
            durum='aktif',
            olusturan_id=current_user.id,
        )
        db.session.add(kayit)
        db.session.commit()
        return True, None
    except IntegrityError as exc:
        db.session.rollback()
        # Postgres UNIQUE violation hatalarini okunabilir mesaja cevir.
        detay = str(getattr(exc, 'orig', exc) or exc).lower()
        if 'users_email_key' in detay or 'email' in detay:
            return False, f"E-posta '{s.get('email') or '-'}' zaten kayıtlı."
        if 'users_username_key' in detay or 'username' in detay:
            return False, f"Kullanıcı adı '{s.get('ogrenci_no')}' zaten kayıtlı."
        if 'ogrenciler_ogrenci_no_key' in detay or 'ogrenci_no' in detay:
            return False, f"Öğrenci No '{s.get('ogrenci_no')}' zaten kayıtlı."
        if 'tc_kimlik' in detay:
            return False, f"TC Kimlik '{s.get('tc_kimlik') or '-'}' zaten kayıtlı."
        # Bilinmeyen unique violation — kisa ozet
        return False, 'Bu kayıt DB\'de çakıştı (mükerrer bir alan var).'
    except Exception as exc:
        db.session.rollback()
        msg = str(exc)
        # SQL detayini kirp — kullanici icin ilk satir yeterli
        msg = msg.split('\n')[0][:200]
        return False, f'Kayıt hatası: {msg}'


@bp.route('/toplu-yukle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def toplu_yukle():
    """Toplu ogrenci yukleme — iki fazli: 'onizle' ve 'kaydet'.

    onizle: Excel yuklenir, parse + dogrula, satirlar hidden JSON alanda geri gonderilir.
    kaydet: Hidden JSON'daki gecerli satirlar DB'ye yazilir (dosya tekrar yuklenmez).
    """
    donemler = KayitDonemi.query.filter_by(aktif=True).order_by(KayitDonemi.ad.desc()).all()
    subeler = Sube.query.filter_by(aktif=True).join(Sinif).order_by(Sinif.seviye, Sube.ad).all()

    onizleme = None
    hatalar_ozet = None
    payload_encoded = None
    secili_donem_id = None
    secili_sube_id = None

    if request.method == 'POST':
        islem = (request.form.get('islem') or 'onizle').strip()

        # Varsayilan donem/sube secimi (her iki faz icin ayni)
        try:
            secili_donem_id = int(request.form.get('donem_id') or 0) or None
        except (TypeError, ValueError):
            secili_donem_id = None
        try:
            secili_sube_id = int(request.form.get('sube_id') or 0) or None
        except (TypeError, ValueError):
            secili_sube_id = None

        varsayilan_donem = KayitDonemi.query.get(secili_donem_id) if secili_donem_id else None
        varsayilan_sube = Sube.query.get(secili_sube_id) if secili_sube_id else None

        # Kullanici donemi hic secmediyse: yalnizca 1 aktif donem varsa onu
        # varsayilan kabul et (yaygın durum — kullanici sıkışmasın).
        if not varsayilan_donem and len(donemler) == 1:
            varsayilan_donem = donemler[0]
            secili_donem_id = varsayilan_donem.id

        if islem == 'onizle':
            # Excel dosyasini parse et
            dosya = request.files.get('excel')
            if not dosya or not dosya.filename:
                flash('Lütfen bir Excel (.xlsx) dosyası seçin.', 'danger')
                return render_template('kayit/ogrenci/toplu_yukle.html',
                                       onizleme=None, hatalar_ozet=None,
                                       basliklar=OGRENCI_BASLIKLAR,
                                       donemler=donemler, subeler=subeler,
                                       secili_donem_id=secili_donem_id,
                                       secili_sube_id=secili_sube_id,
                                       payload=None)
            try:
                satirlar = excel_oku(dosya, OGRENCI_BASLIKLAR)
            except ValueError as exc:
                flash(str(exc), 'danger')
                return render_template('kayit/ogrenci/toplu_yukle.html',
                                       onizleme=None, hatalar_ozet=None,
                                       basliklar=OGRENCI_BASLIKLAR,
                                       donemler=donemler, subeler=subeler,
                                       secili_donem_id=secili_donem_id,
                                       secili_sube_id=secili_sube_id,
                                       payload=None)
            except Exception as exc:
                flash(f'Excel okunamadi: {exc}', 'danger')
                return render_template('kayit/ogrenci/toplu_yukle.html',
                                       onizleme=None, hatalar_ozet=None,
                                       basliklar=OGRENCI_BASLIKLAR,
                                       donemler=donemler, subeler=subeler,
                                       secili_donem_id=secili_donem_id,
                                       secili_sube_id=secili_sube_id,
                                       payload=None)

            _toplu_dogrula(satirlar, varsayilan_donem, varsayilan_sube)
            gecerli = [s for s in satirlar if not s['_hatalar']]
            hatali = [s for s in satirlar if s['_hatalar']]
            hatalar_ozet = {
                'toplam': len(satirlar),
                'gecerli': len(gecerli),
                'hatali': len(hatali),
            }
            onizleme = satirlar
            # Yalnizca gecerli satirlari payload'a koy — kaydet adiminda onlar islenir.
            payload_encoded = _encode_payload(gecerli) if gecerli else None

        elif islem == 'kaydet':
            # Satirlari once duzenlenebilir form alanlarindan oku; bos ise
            # geriye uyumluluk icin base64 payload'a bak.
            satirlar = _form_alanlarindan_satirlar(request.form)
            if not satirlar:
                payload_raw = request.form.get('payload') or ''
                satirlar = _decode_payload(payload_raw)

            if not satirlar:
                flash('Kaydedilecek satır bulunamadı. Lütfen önce dosyayı yükleyip önizleyin.', 'warning')
                return redirect(url_for('kayit.ogrenci.toplu_yukle'))

            # Tamamen bos satirlari at
            satirlar = [s for s in satirlar if any(
                s.get(b['key']) for b in OGRENCI_BASLIKLAR)]

            # Kullanici inline duzenleme sonrasi yeniden dogrulama yap
            _toplu_dogrula(satirlar, varsayilan_donem, varsayilan_sube)

            eklenen = 0
            kalan_satirlar = []  # Kaydedilemeyen + hatali olan
            for s in satirlar:
                if s['_hatalar']:
                    kalan_satirlar.append(s)
                    continue
                ok, hata = _ogrenci_kaydet_bir(s)
                if ok:
                    eklenen += 1
                else:
                    s['_hatalar'].append(hata or 'Bilinmeyen hata.')
                    kalan_satirlar.append(s)

            if eklenen:
                flash(
                    f'{eklenen} öğrenci başarıyla eklendi.' +
                    (f' {len(kalan_satirlar)} satır hâlâ düzeltilmesi gerekiyor.'
                     if kalan_satirlar else ''),
                    'success')

            if not kalan_satirlar:
                return redirect(url_for('kayit.ogrenci.liste'))

            # Hatali/kaydedilemeyen satirlari tekrar onizlemeye koy —
            # kullanici inline duzeltip tekrar Kaydet'e bassin.
            onizleme = kalan_satirlar
            hatalar_ozet = {
                'toplam': len(kalan_satirlar),
                'gecerli': 0,
                'hatali': len(kalan_satirlar),
            }
            if not eklenen:
                flash('Hiç öğrenci eklenemedi. Aşağıdaki hataları düzeltin ve tekrar kaydedin.', 'warning')

    _satir_to_display(onizleme or [])
    return render_template('kayit/ogrenci/toplu_yukle.html',
                           onizleme=onizleme, hatalar_ozet=hatalar_ozet,
                           basliklar=OGRENCI_BASLIKLAR,
                           donemler=donemler, subeler=subeler,
                           secili_donem_id=secili_donem_id,
                           secili_sube_id=secili_sube_id,
                           payload=payload_encoded)


@bp.route('/karteks-yukle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def karteks_yukle():
    """
    Karteks görselini yükler, geçici olarak session'a koyar ve yeni kayıt
    sayfasına yönlendirir. Yeni kayıt sayfası karteksi yan panelde gösterir,
    kullanıcı bilgileri görüntüye bakarak elle doldurur. Form kaydedilince
    karteks oluşturulan öğrenciye belge olarak bağlanır.
    """
    form = KarteksYukleForm()
    if form.validate_on_submit():
        try:
            rel_path, orijinal = _save_belge_dosyasi(form.karteks.data, 'karteks')
        except Exception as exc:
            flash(f'Dosya kaydedilemedi: {exc}', 'danger')
            return render_template('kayit/ogrenci/karteks_yukle.html', form=form)

        session['karteks_dosya'] = {'rel': rel_path, 'orijinal': orijinal}
        flash(
            'Karteks yüklendi. Sağdaki forma karteks görüntüsüne bakarak '
            'bilgileri doldurun.',
            'success'
        )
        return redirect(url_for('kayit.ogrenci.yeni_kayit'))

    return render_template('kayit/ogrenci/karteks_yukle.html', form=form)


@bp.route('/karteks-onizleme')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def karteks_onizleme():
    """Yeni kayıt akışında session'daki karteks görselini serve eder."""
    karteks = session.get('karteks_dosya')
    if not karteks:
        abort(404)

    klasor = current_app.config['UPLOAD_FOLDER']
    full = os.path.join(klasor, karteks['rel'])
    if not os.path.exists(full):
        abort(404)

    return send_from_directory(klasor, karteks['rel'], as_attachment=False)


@bp.route('/yeni', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def yeni_kayit():
    # Karteks varsa yan panelde göstereceğiz, kayıt sonunda öğrenciye bağlayacağız
    karteks_dosya = session.get('karteks_dosya')

    form = OgrenciKayitForm()

    donemler = KayitDonemi.query.filter_by(aktif=True).all()
    form.donem_id.choices = [(d.id, d.ad) for d in donemler]

    subeler = Sube.query.filter_by(aktif=True).join(Sinif).order_by(Sinif.seviye, Sube.ad).all()
    form.sube_id.choices = [(s.id, s.tam_ad) for s in subeler]

    if form.validate_on_submit():
        # Tenant ogrenci limit kontrolu
        from app.tenancy.limitler import ogrenci_limit_kontrol
        izin, mesaj = ogrenci_limit_kontrol()
        if not izin:
            flash(mesaj, 'danger')
            return render_template('kayit/ogrenci/kayit_form.html',
                                   form=form, baslik='Yeni Öğrenci Kaydı',
                                   karteks_aktif=bool(karteks_dosya),
                                   karteks_dosya=karteks_dosya)
        # Öğrenci no kontrolü
        mevcut = Ogrenci.query.filter_by(ogrenci_no=form.ogrenci_no.data).first()
        if mevcut:
            flash('Bu öğrenci numarası zaten kayıtlı.', 'danger')
            return render_template('kayit/ogrenci/kayit_form.html',
                                   form=form, baslik='Yeni Öğrenci Kaydı',
                                   karteks_aktif=bool(karteks_dosya),
                                   karteks_dosya=karteks_dosya)

        # Kontenjan kontrolü
        sube = Sube.query.get(form.sube_id.data)
        if sube and sube.bos_kontenjan <= 0:
            flash(f'{sube.tam_ad} kontenjanı dolu.', 'danger')
            return render_template('kayit/ogrenci/kayit_form.html',
                                   form=form, baslik='Yeni Öğrenci Kaydı',
                                   karteks_aktif=bool(karteks_dosya),
                                   karteks_dosya=karteks_dosya)

        # Otomatik kullanıcı hesabı oluştur (username = öğrenci no)
        username = form.ogrenci_no.data
        varsayilan_sifre = form.tc_kimlik.data if form.tc_kimlik.data else form.ogrenci_no.data
        user = User(
            username=username,
            email=form.email.data or f"{username}@ogrenci.obs",
            ad=form.ad.data,
            soyad=form.soyad.data,
            rol='ogrenci',
            aktif=True
        )
        user.set_password(varsayilan_sifre)
        db.session.add(user)
        db.session.flush()

        ogrenci = Ogrenci(
            user_id=user.id,
            ogrenci_no=form.ogrenci_no.data,
            tc_kimlik=form.tc_kimlik.data or None,
            ad=form.ad.data,
            soyad=form.soyad.data,
            cinsiyet=form.cinsiyet.data or None,
            dogum_tarihi=form.dogum_tarihi.data,
            dogum_yeri=form.dogum_yeri.data or None,
            kan_grubu=form.kan_grubu.data or None,
            telefon=form.telefon.data or None,
            email=form.email.data or None,
            adres=form.adres.data or None,
            sinif=sube.sinif.ad if sube else None
        )
        db.session.add(ogrenci)
        db.session.flush()

        # Kayıt kaydı oluştur
        kayit = OgrenciKayit(
            ogrenci_id=ogrenci.id,
            donem_id=form.donem_id.data,
            sube_id=form.sube_id.data,
            kayit_tarihi=date.today(),
            durum='aktif',
            olusturan_id=current_user.id
        )
        db.session.add(kayit)

        # Varsayılan belge kayıtları oluştur
        varsayilan_belgeler = [
            'nufus_cuzdani', 'ogrenim_belgesi', 'fotograf',
            'saglik_raporu', 'ikametgah'
        ]
        for belge_turu in varsayilan_belgeler:
            db.session.add(OgrenciBelge(
                ogrenci_id=ogrenci.id,
                belge_turu=belge_turu,
                teslim_edildi=False
            ))

        # Karteks ile gelmişse dosyayı belge olarak kaydet
        if karteks_dosya:
            db.session.add(OgrenciBelge(
                ogrenci_id=ogrenci.id,
                belge_turu='karteks',
                teslim_edildi=True,
                teslim_tarihi=date.today(),
                dosya_yolu=karteks_dosya.get('rel'),
                orijinal_ad=karteks_dosya.get('orijinal'),
                aciklama='Kayıt sırasında karteks olarak yüklendi.'
            ))

        db.session.commit()

        # Karteks session'ını temizle
        session.pop('karteks_dosya', None)

        flash(f'{ogrenci.tam_ad} başarıyla kaydedildi. '
              f'Giriş bilgileri — Kullanıcı adı: {username}, Şifre: {varsayilan_sifre}', 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci.id))

    return render_template('kayit/ogrenci/kayit_form.html',
                           form=form, baslik='Yeni Öğrenci Kaydı',
                           karteks_aktif=bool(karteks_dosya),
                           karteks_dosya=karteks_dosya)


@bp.route('/karteks-iptal', methods=['POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def karteks_iptal():
    """Session'daki karteks görselini ve geçici dosyayı temizler."""
    karteks_dosya = session.pop('karteks_dosya', None)
    if karteks_dosya:
        try:
            full = os.path.join(current_app.config['UPLOAD_FOLDER'],
                                karteks_dosya['rel'])
            if os.path.exists(full):
                os.remove(full)
        except OSError:
            pass
    flash('Karteks kaldırıldı.', 'info')
    return redirect(url_for('kayit.ogrenci.yeni_kayit'))


@bp.route('/<int:ogrenci_id>')
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def detay(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    kayitlar = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci_id
    ).order_by(OgrenciKayit.kayit_tarihi.desc()).all()

    veliler = VeliBilgisi.query.filter_by(ogrenci_id=ogrenci_id).all()
    belgeler = OgrenciBelge.query.filter_by(ogrenci_id=ogrenci_id).all()

    aktif_kayit = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci_id, durum='aktif'
    ).first()

    return render_template('kayit/ogrenci/detay.html',
                           ogrenci=ogrenci,
                           kayitlar=kayitlar,
                           veliler=veliler,
                           belgeler=belgeler,
                           aktif_kayit=aktif_kayit)


@bp.route('/<int:ogrenci_id>/duzenle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def duzenle(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    aktif_kayit = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci_id, durum='aktif'
    ).first()

    form = OgrenciDuzenleForm(obj=ogrenci)

    # Donem + sube secenekleri
    donemler = KayitDonemi.query.filter_by(aktif=True).order_by(KayitDonemi.ad.desc()).all()
    subeler = Sube.query.filter_by(aktif=True).join(Sinif).order_by(Sinif.seviye, Sube.ad).all()
    form.donem_id.choices = [(0, '-- Seçiniz --')] + [(d.id, d.ad) for d in donemler]
    form.sube_id.choices = [(0, '-- Seçiniz --')] + [(s.id, s.tam_ad) for s in subeler]

    # GET: aktif kaydin degerlerini secili hale getir
    if request.method == 'GET' and aktif_kayit:
        form.donem_id.data = aktif_kayit.donem_id
        form.sube_id.data = aktif_kayit.sube_id

    if form.validate_on_submit():
        ogrenci.ogrenci_no = form.ogrenci_no.data
        ogrenci.tc_kimlik = form.tc_kimlik.data or None
        ogrenci.ad = form.ad.data
        ogrenci.soyad = form.soyad.data
        ogrenci.cinsiyet = form.cinsiyet.data or None
        ogrenci.dogum_tarihi = form.dogum_tarihi.data
        ogrenci.dogum_yeri = form.dogum_yeri.data or None
        ogrenci.kan_grubu = form.kan_grubu.data or None
        ogrenci.telefon = form.telefon.data or None
        ogrenci.email = form.email.data or None
        ogrenci.adres = form.adres.data or None

        # Donem / sube guncelleme
        yeni_donem_id = form.donem_id.data or 0
        yeni_sube_id = form.sube_id.data or 0
        kayit_mesaji = None

        if yeni_donem_id and yeni_sube_id:
            if aktif_kayit:
                if (aktif_kayit.donem_id != yeni_donem_id or
                        aktif_kayit.sube_id != yeni_sube_id):
                    aktif_kayit.donem_id = yeni_donem_id
                    aktif_kayit.sube_id = yeni_sube_id
                    kayit_mesaji = 'Dönem/şube güncellendi.'
            else:
                # Aktif kayit yok — yeni olustur
                yeni_kayit = OgrenciKayit(
                    ogrenci_id=ogrenci.id,
                    donem_id=yeni_donem_id,
                    sube_id=yeni_sube_id,
                    kayit_tarihi=date.today(),
                    durum='aktif',
                    olusturan_id=current_user.id,
                )
                db.session.add(yeni_kayit)
                kayit_mesaji = 'Öğrenciye aktif kayıt oluşturuldu.'

            # Ogrenci.sinif string alanini da yeni subenin sinifina ayarla
            sube = Sube.query.get(yeni_sube_id)
            if sube:
                ogrenci.sinif = sube.sinif.ad

        db.session.commit()
        flash('Öğrenci bilgileri güncellendi.' +
              (f' {kayit_mesaji}' if kayit_mesaji else ''), 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    return render_template('kayit/ogrenci/duzenle.html',
                           form=form, ogrenci=ogrenci,
                           aktif_kayit=aktif_kayit)


@bp.route('/<int:ogrenci_id>/durum', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def durum_degistir(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    aktif_kayit = OgrenciKayit.query.filter_by(
        ogrenci_id=ogrenci_id, durum='aktif'
    ).first()

    if not aktif_kayit:
        flash('Bu öğrencinin aktif kaydı bulunmuyor.', 'warning')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    form = DurumDegistirForm()

    if form.validate_on_submit():
        aktif_kayit.durum = form.durum.data
        aktif_kayit.durum_tarihi = date.today()
        aktif_kayit.durum_aciklama = form.aciklama.data

        if form.durum.data in ('mezun', 'nakil_giden', 'kayit_silindi'):
            ogrenci.aktif = False

        db.session.commit()
        label, _ = aktif_kayit.durum_badge
        flash(f'Öğrenci durumu "{label}" olarak güncellendi.', 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    return render_template('kayit/ogrenci/durum_degistir.html',
                           form=form, ogrenci=ogrenci, aktif_kayit=aktif_kayit)


@bp.route('/<int:ogrenci_id>/kalici-sil', methods=['POST'])
@login_required
@role_required('admin', 'yonetici')
def kalici_sil(ogrenci_id):
    """Ogrenciyi ve TUM bagli kayitlarini kalici olarak sil.

    Sadece admin yapabilir. Onay icin form'da type-to-confirm pattern kullanilir:
    kullanici ogrencinin ogrenci_no'sunu dogru girmelidir.

    Silinenler:
     - FK'si ogrenciler.id'ye bagli tum satirlar (muhasebe, devamsizlik,
       rehberlik, saglik, servis, kulup, sinav katilimlari, bildirim vs.)
     - OgrenciBelge dosyalari (disk)
     - Orphan kalan veli User'lari (sadece bu ogrenci icin olusturulmus ve
       baska ogrencinin velisi olmayanlar)
     - Ogrenci.user_id varsa o User hesabi
     - Ogrenci satirinin kendisi
    """
    from sqlalchemy import inspect as sa_inspect, text
    from app.models.denetim import DenetimLog

    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)

    # Onay: ogrenci_no eslesmesi
    onay_no = (request.form.get('onay_no') or '').strip()
    if onay_no != (ogrenci.ogrenci_no or '').strip():
        flash('Onay için öğrenci numarasını doğru girmelisiniz. Silme iptal edildi.',
              'danger')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    # Log icin detay metni hazirla (silmeden once)
    ad_soyad = ogrenci.tam_ad
    ogrenci_no = ogrenci.ogrenci_no
    ogrenci_user_id = ogrenci.user_id

    # 1) Belge dosyalarini disk'ten sil
    belge_dosyalari = [b.dosya_yolu for b in
                       OgrenciBelge.query.filter_by(ogrenci_id=ogrenci_id).all()
                       if b.dosya_yolu]
    silinen_dosya = 0
    for yol in belge_dosyalari:
        try:
            tam_yol = os.path.join(current_app.config.get('UPLOAD_FOLDER', ''), yol) \
                if not os.path.isabs(yol) else yol
            if os.path.exists(tam_yol):
                os.remove(tam_yol)
                silinen_dosya += 1
        except OSError:
            pass  # sessiz gec, DB satiri zaten silinecek

    # 2) Orphan-kontrolu icin veli user_id'lerini toplan (bu ogrenciye bagli)
    veli_user_ids = [v.user_id for v in
                     VeliBilgisi.query.filter_by(ogrenci_id=ogrenci_id).all()
                     if v.user_id]

    # 3) BFS: ogrenciler[oid] kokunden baslayarak tum downstream tablolari
    #    tespit et. Her tablonun hangi PK'lerinin hedeflendigini topla, sonra
    #    leaf'ten (derinlik buyuk) kok'e dogru sil.
    bind = db.session.get_bind()
    insp = sa_inspect(bind)

    # Tum FK iliskilerini indeksle: child_table -> [(child_col, parent_table, parent_col), ...]
    fk_index: dict[str, list[tuple[str, str, str]]] = {}
    for t in insp.get_table_names():
        for fk in insp.get_foreign_keys(t):
            parent = fk.get('referred_table')
            ccols = fk.get('constrained_columns') or []
            pcols = fk.get('referred_columns') or []
            if parent and ccols and pcols:
                fk_index.setdefault(t, []).append((ccols[0], parent, pcols[0]))

    # BFS: silinmesi gereken (tablo, ids) kumesini ve sira (derinlik) bilgisini tut
    hedef: dict[str, set] = {'ogrenciler': {ogrenci_id}}
    derinlik: dict[str, int] = {'ogrenciler': 0}
    sira = [('ogrenciler', 0)]
    i = 0
    while i < len(sira):
        parent_tablo, d = sira[i]
        i += 1
        parent_ids = list(hedef.get(parent_tablo, set()))
        if not parent_ids:
            continue
        # Bu parent'a FK'si olan tum child tablolari bul
        for child_table, fklar in fk_index.items():
            for child_col, pt, pc in fklar:
                if pt != parent_tablo or pc != 'id':
                    continue
                # IN (...) icin parametreleri explicit expand
                placeholders = ','.join(f':p{k}' for k in range(len(parent_ids)))
                params = {f'p{k}': v for k, v in enumerate(parent_ids)}
                sql = (f'SELECT "id" FROM "{child_table}" '
                       f'WHERE "{child_col}" IN ({placeholders})')
                try:
                    child_ids = [r[0] for r in db.session.execute(
                        text(sql), params).all()]
                except Exception:
                    child_ids = []
                if not child_ids:
                    continue
                onceki = hedef.setdefault(child_table, set())
                yeni = set(child_ids) - onceki
                if yeni:
                    onceki |= yeni
                    # Derinligi guncelle (max)
                    derinlik[child_table] = max(derinlik.get(child_table, 0),
                                                 d + 1)
                    sira.append((child_table, d + 1))

    # Silme: en buyuk derinlikten basla, koke dogru git. 'ogrenciler' kokunu
    # bu asamada silme — daha sonra ORM ile silecegiz (6. adim).
    silinen_tablolar: dict[str, int] = {}
    tablo_sirasi = sorted(
        [(t, derinlik.get(t, 0)) for t in hedef.keys() if t != 'ogrenciler'],
        key=lambda x: -x[1],
    )
    for tablo, _d in tablo_sirasi:
        ids = list(hedef[tablo])
        if not ids:
            continue
        placeholders = ','.join(f':p{k}' for k in range(len(ids)))
        params = {f'p{k}': v for k, v in enumerate(ids)}
        res = db.session.execute(
            text(f'DELETE FROM "{tablo}" WHERE "id" IN ({placeholders})'),
            params,
        )
        if res.rowcount:
            silinen_tablolar[tablo] = res.rowcount

    # 4) Orphan veli User'larini sil (bu ogrenciye ozel acilmis, baska
    #    ogrencinin velisi olmayan)
    silinen_veli_user = 0
    for vuid in veli_user_ids:
        # VeliBilgisi adim 3'te silindigi icin baska bagli kayit varsa User
        # hala referansli olur (COUNT 0 ise orphan):
        kalan = db.session.execute(
            text('SELECT COUNT(*) FROM veli_bilgileri WHERE user_id = :uid'),
            {'uid': vuid},
        ).scalar()
        if kalan == 0:
            # Opsiyonel: rol'u 'veli' degilse (ornegin yanlislikla atanmis
            # admin), bu safety check koru. Biz sadece veli rolunde olanlari
            # silelim.
            u = User.query.get(vuid)
            if u and u.rol == 'veli':
                db.session.delete(u)
                silinen_veli_user += 1

    # 5) Ogrenci.user_id varsa o User'i da sil (cascade ile push_abonelik,
    #    KullaniciModulIzin temizlenir; Bildirim cascade yoksa manuel)
    silinen_ogrenci_user = 0
    if ogrenci_user_id:
        db.session.execute(
            text('DELETE FROM bildirimler WHERE kullanici_id = :uid'),
            {'uid': ogrenci_user_id},
        )
        u = User.query.get(ogrenci_user_id)
        if u and u.rol == 'ogrenci':
            db.session.delete(u)
            silinen_ogrenci_user = 1

    # 6) Ogrenci satirinin kendisini sil
    db.session.delete(ogrenci)

    # 7) Denetim log
    detay_ozet = (
        f'Ogrenci kalici silindi: {ad_soyad} (#{ogrenci_no}). '
        f'Silinen: {silinen_dosya} belge dosyasi, '
        f'{silinen_veli_user} veli hesabi, '
        f'{silinen_ogrenci_user} ogrenci hesabi. '
        f'Tablolar: ' + ', '.join(f'{k}={v}' for k, v in
                                  sorted(silinen_tablolar.items()))
    )
    db.session.add(DenetimLog(
        kullanici_id=current_user.id,
        islem='silme',
        modul='kayit.ogrenci',
        detay=detay_ozet,
        ip_adresi=request.remote_addr,
    ))
    db.session.commit()

    flash(f'Öğrenci {ad_soyad} (#{ogrenci_no}) ve tüm kayıtları kalıcı olarak silindi.',
          'success')
    return redirect(url_for('kayit.ogrenci.liste'))


@bp.route('/<int:ogrenci_id>/veli-ekle', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'muhasebeci', 'yonetici')
def veli_ekle(ogrenci_id):
    ogrenci = Ogrenci.query.get_or_404(ogrenci_id)
    form = VeliForm()

    if form.validate_on_submit():
        # Otomatik veli kullanıcı hesabı oluştur
        # Username: veli_<ogrenci_no>_<yakinlik> (ör: veli_1001_anne)
        username = f"veli_{ogrenci.ogrenci_no}_{form.yakinlik.data}"
        varsayilan_sifre = form.tc_kimlik.data if form.tc_kimlik.data else username
        user = User(
            username=username,
            email=form.email.data or f"{username}@veli.obs",
            ad=form.ad.data,
            soyad=form.soyad.data,
            rol='veli',
            aktif=True
        )
        user.set_password(varsayilan_sifre)
        db.session.add(user)
        db.session.flush()

        veli = VeliBilgisi(
            user_id=user.id,
            ogrenci_id=ogrenci_id,
            yakinlik=form.yakinlik.data,
            tc_kimlik=form.tc_kimlik.data or None,
            ad=form.ad.data,
            soyad=form.soyad.data,
            telefon=form.telefon.data or None,
            email=form.email.data or None,
            meslek=form.meslek.data or None,
            adres=form.adres.data or None
        )
        db.session.add(veli)

        # Ogrenci tablosundaki veli bilgisini de güncelle
        if not ogrenci.veli_ad:
            ogrenci.veli_ad = f"{form.ad.data} {form.soyad.data}"
            ogrenci.veli_telefon = form.telefon.data

        db.session.commit()
        flash(f'Veli bilgisi başarıyla eklendi. '
              f'Giriş bilgileri — Kullanıcı adı: {username}, Şifre: {varsayilan_sifre}', 'success')
        return redirect(url_for('kayit.ogrenci.detay', ogrenci_id=ogrenci_id))

    return render_template('kayit/ogrenci/veli_form.html',
                           form=form, ogrenci=ogrenci, baslik='Veli Ekle')
