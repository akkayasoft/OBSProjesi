"""Yayinci deneme sonuc PDF'lerinden satir-bazli parser.

Simdilik destekli format(lar):
  - "X Yayinlari - Okul Net Listesi (LGS sirali)"
    Sutunlar: Sira, O.No, Isim, Sinif, (D Y N) x 6 ders, Toplam D/Y/N,
    LGS Puani, Dereceler (Snf Okul Ilce Il Genel).
    Dersler sirasiyla: Turkce, Tarih, Din K.ve A.B., Ingilizce, Matematik, Fen.

PDF metin tabanli oldugu icin OCR gerekmiyor; pdfplumber'in extract_text()
ciktisini satir satir regex ile cozuyoruz. Ayni PDF'te aldigimiz tum
ogrenci satirlari donuyor; sistemdeki ogrenci kaydiyla eslestirmek
(ogrenci_no, ad-soyad fallback) ithalat katmaninin isi.

Turkce ondalik '20,00' -> 20.00 seklinde donusturulur. Yan yana gelip
birbirine yapismis desimaller (ornek: '90,00500,000') unglue edilir.
"""
from __future__ import annotations
import io
import re
from dataclasses import dataclass, field
from typing import Optional


# 8-XX / 8-A / 8-B gibi sinif etiketi — 7./9./10... icin degisebilir
SINIF_RE = r'\d{1,2}-[A-ZĞÜŞİÖÇ]+'

# Satir pattern: sira + ono + isim + sinif + gerisi
ROW_RE = re.compile(
    rf'^(\d+)\s+(\d+)\s+(.+?)\s+({SINIF_RE})\s+(.+)$'
)

# Ders sirasi (X Yayinlari, LGS)
DEFAULT_DERS_KODLARI = [
    'turkce', 'inkilap', 'din', 'ingilizce', 'matematik', 'fen'
]


@dataclass
class PdfOgrenciSatiri:
    sira: int
    ogrenci_no: int
    isim: str
    sinif: str
    # Her ders icin (dogru, yanlis, net)
    dersler: list[tuple[int, int, float]] = field(default_factory=list)
    toplam_dogru: int = 0
    toplam_yanlis: int = 0
    toplam_net: float = 0.0
    puan: float = 0.0

    @property
    def ders_sozluk(self) -> dict[str, tuple[int, int, float]]:
        out = {}
        for i, (d, y, n) in enumerate(self.dersler):
            if i < len(DEFAULT_DERS_KODLARI):
                out[DEFAULT_DERS_KODLARI[i]] = (d, y, n)
        return out


@dataclass
class PdfIthalatSonuc:
    """parse_pdf cagrisi sonucu."""
    # Basariyla parse edilen ogrenci satirlari
    satirlar: list[PdfOgrenciSatiri]
    # Atlanan satirlar (eksik ders, bozuk satir vs.) — audit/log icin
    atlananlar: list[dict]
    # PDF basliktan yakalanan sinav ad, okul ad vs.
    sinav_adi: Optional[str] = None
    okul_adi: Optional[str] = None
    il: Optional[str] = None
    ilce: Optional[str] = None
    # PDF icinden tespit edilen yayinci adi (otomatik)
    yayinci: Optional[str] = None
    yayinci_kaynak: Optional[str] = None  # 'metni' | 'metadata' | None


# --- Yayinci tespiti -------------------------------------------------------
# PDF basligi/altligindan yayinci adi cikarmak icin desenler. Once metadata
# (Author, Producer, Title), sonra PDF metni icinde aranir.

# Onemli: liste sirasiyla kontrol edilir (en spesifik once). Ad eslestiginde
# ham yazim tercih edilir; bulunamayanda regex ile yakalanan jenerik isim
# dondurulur.
BILINEN_YAYINCILAR = [
    'Limit Yayinlari', 'Final Yayinlari', 'Bilfen Yayinlari',
    'BilgiSarmal', 'Apotemi Yayinlari', 'Tonguc Akademi',
    'Karekok Yayinlari', 'Esen Yayinlari', 'Newton Yayinlari',
    'Hiz Yayinlari', 'Sinav Yayinlari', 'Doga Yayinlari',
    '3D Yayinlari', 'Test Okul', 'Pegasus Yayinlari',
    'Endemik Yayinlari', 'Akilli Adam Yayinlari',
    'Cap Yayinlari', 'Nartest', 'Palme Yayinlari',
]


def _normalize_tr(s: str) -> str:
    """Karsilastirma icin Turkce karakter normalize."""
    s = (s or '').lower()
    for a, b in (('ı', 'i'), ('İ', 'i'), ('ş', 's'), ('Ş', 's'),
                 ('ğ', 'g'), ('Ğ', 'g'), ('ü', 'u'), ('Ü', 'u'),
                 ('ö', 'o'), ('Ö', 'o'), ('ç', 'c'), ('Ç', 'c')):
        s = s.replace(a, b)
    return s


def tespit_yayinci(metin: str, metadata: dict | None = None) -> tuple[str | None, str | None]:
    """PDF metninden ve/veya metadata'sindan yayinci adini cikar.

    Donus: (yayinci_adi, kaynak)
        kaynak: 'metadata' | 'metni' | None
    """
    metadata = metadata or {}

    # 1) Metadata fields
    for key in ('Author', 'Producer', 'Creator', 'Title', 'Subject'):
        val = metadata.get(key) or metadata.get(key.lower())
        if not val:
            continue
        nval = _normalize_tr(str(val))
        for ad in BILINEN_YAYINCILAR:
            if _normalize_tr(ad) in nval:
                return ad, 'metadata'

    if not metin:
        return None, None

    # 2) Metin icinde bilinen isim ara (case-insensitive Turkce-normalize)
    nmetin = _normalize_tr(metin)
    for ad in BILINEN_YAYINCILAR:
        if _normalize_tr(ad) in nmetin:
            return ad, 'metni'

    # 3) Jenerik regex: "<Bir-Iki kelime> Yayinlari" yakala
    m = re.search(
        r'([A-ZĞÜŞİÖÇ][A-Za-zĞÜŞİÖÇğüşıöç0-9]{1,15}'
        r'(?:\s+[A-ZĞÜŞİÖÇ][A-Za-zĞÜŞİÖÇğüşıöç0-9]{1,15}){0,2})'
        r'\s+Yayınları',
        metin,
    )
    if m:
        return m.group(0).strip(), 'metni'
    # Turkce-asciisiz alternatif
    m = re.search(
        r'([A-Za-z0-9]{2,20}(?:\s+[A-Za-z0-9]{2,20}){0,2})\s+Yayinlari',
        metin,
    )
    if m:
        return m.group(0).strip(), 'metni'

    # 4) "Akademi" eki (Tonguc Akademi gibi)
    m = re.search(
        r'([A-ZĞÜŞİÖÇ][A-Za-zĞÜŞİÖÇğüşıöç]{2,15})\s+Akademi',
        metin,
    )
    if m:
        return m.group(0).strip(), 'metni'

    return None, None


def _tokenize(rest: str) -> list[str]:
    """'88,67497,959' gibi yapismis Turkce desimalleri parcala."""
    # Bir ',XX' hemen ardindan '\d{3},\d{3}' geliyorsa arasina bosluk koy
    rest = re.sub(r'(,\d{2})(?=\d{3},\d{3})', r'\1 ', rest)
    return rest.split()


def _parse_row(line: str) -> dict:
    """Bir satiri cozumle. Basarili ise PdfOgrenciSatiri (dict turunde),
    degil ise {'_skip': True, 'neden': ...}. Hic eslesmezse None."""
    m = ROW_RE.match(line)
    if not m:
        return None
    sira, ono, isim, sinif, rest = m.groups()
    tokens = _tokenize(rest)
    # Tam satir: 6*(D,Y,N) + (tD,tY,tN) + puan + 5 derece = 27
    # Minimum: ders eksikse de en az 22 olmayani atla
    if len(tokens) < 22:
        return {'_skip': True, 'sira': sira, 'ono': ono, 'isim': isim.strip(),
                'sinif': sinif, 'neden': f'az token ({len(tokens)})',
                'raw': line.strip()}
    dersler: list[tuple[int, int, float]] = []
    idx = 0
    try:
        for _ in range(6):
            d = int(tokens[idx])
            y = int(tokens[idx + 1])
            n = float(tokens[idx + 2].replace(',', '.'))
            dersler.append((d, y, n))
            idx += 3
        tD = int(tokens[idx]); tY = int(tokens[idx + 1])
        tN = float(tokens[idx + 2].replace(',', '.'))
        idx += 3
        puan = float(tokens[idx].replace(',', '.'))
    except (ValueError, IndexError) as e:
        return {'_skip': True, 'sira': sira, 'ono': ono, 'isim': isim.strip(),
                'sinif': sinif, 'neden': f'parse hata: {e}',
                'raw': line.strip()}
    return {
        'sira': int(sira), 'ogrenci_no': int(ono), 'isim': isim.strip(),
        'sinif': sinif, 'dersler': dersler,
        'toplam_dogru': tD, 'toplam_yanlis': tY, 'toplam_net': tN,
        'puan': puan,
    }


def parse_pdf(data: bytes) -> PdfIthalatSonuc:
    """PDF byte'larindan ogrenci satirlarini cikar.

    Tum satirlarin (sira, ogrenci_no, isim) uclusu uzerinden dedup yapilir;
    PDF'te bazen son sayfada aynı satir iki kere basiliyor.
    """
    import pdfplumber

    satirlar: list[PdfOgrenciSatiri] = []
    atlananlar: list[dict] = []
    seen: set[tuple[int, int, str]] = set()

    sinav_adi = okul_adi = il = ilce = None

    yayinci_metni_buf: list[str] = []
    pdf_metadata: dict = {}

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        try:
            pdf_metadata = pdf.metadata or {}
        except Exception:
            pdf_metadata = {}
        for pg in pdf.pages:
            text = pg.extract_text() or ''
            # Ilk 2 sayfanin tam metni + sonraki sayfalarin ilk 5 satiri
            # yayinci tespiti icin yeterlidir
            if pg.page_number <= 2:
                yayinci_metni_buf.append(text)
            else:
                yayinci_metni_buf.append('\n'.join(text.split('\n')[:5]))
            for raw in text.split('\n'):
                line = raw.strip()
                if not line:
                    continue
                # Ortalamalar/baslik satirlarini atla
                if 'Ortalama' in line or line.startswith('%'):
                    continue

                # Baslik (header) — ornek:
                # "SANLIURFA KARAKOPRU OZEL ... 8. SINIF LGS 5.UYGULAMA 91 91 91 1249"
                if okul_adi is None and 'LGS' in line.upper() \
                        and 'UYGULAMA' in line.upper():
                    hm = re.match(r'^(\S+)\s+(\S+)\s+(.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$',
                                  line)
                    if hm:
                        il = hm.group(1)
                        ilce = hm.group(2)
                        # "OZEL ... 8. SINIF LGS 5.UYGULAMA" — sinav_adi'ni
                        # LGS kelimesinden itibaren al, okul_adi oncesi
                        gerisi = hm.group(3)
                        # "8. SINIF" ya da "LGS" kelimesine kadar olan okul ad
                        ayir = re.search(r'(\d+\.?\s*SINIF\s+LGS|LGS)\s+', gerisi)
                        if ayir:
                            okul_adi = gerisi[:ayir.start()].strip()
                            sinav_adi = gerisi[ayir.start():].strip()
                        else:
                            okul_adi = gerisi.strip()

                r = _parse_row(line)
                if r is None:
                    continue
                if r.get('_skip'):
                    atlananlar.append(r)
                    continue
                key = (r['sira'], r['ogrenci_no'], r['isim'])
                if key in seen:
                    continue
                seen.add(key)
                satirlar.append(PdfOgrenciSatiri(
                    sira=r['sira'], ogrenci_no=r['ogrenci_no'],
                    isim=r['isim'], sinif=r['sinif'],
                    dersler=r['dersler'],
                    toplam_dogru=r['toplam_dogru'],
                    toplam_yanlis=r['toplam_yanlis'],
                    toplam_net=r['toplam_net'],
                    puan=r['puan'],
                ))

    yayinci, yayinci_kaynak = tespit_yayinci(
        '\n'.join(yayinci_metni_buf), pdf_metadata,
    )

    return PdfIthalatSonuc(
        satirlar=satirlar, atlananlar=atlananlar,
        sinav_adi=sinav_adi, okul_adi=okul_adi, il=il, ilce=ilce,
        yayinci=yayinci, yayinci_kaynak=yayinci_kaynak,
    )
