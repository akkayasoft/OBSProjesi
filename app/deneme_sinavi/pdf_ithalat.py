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

    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for pg in pdf.pages:
            text = pg.extract_text() or ''
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

    return PdfIthalatSonuc(
        satirlar=satirlar, atlananlar=atlananlar,
        sinav_adi=sinav_adi, okul_adi=okul_adi, il=il, ilce=ilce,
    )
