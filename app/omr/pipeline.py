"""OMR pipeline: fotograf veya PDF'ten okunmus cevap kagidini cozer.

Akis:
    1. Goruntuyu yukle (jpg/png/pdf-as-image)
    2. 4 kose kalibrasyon markerini bul (en buyuk 4 siyah kare konturu)
    3. Perspektif donusumu ile mm-olcekli "duz" sayfaya cevir
    4. layout.py'den bubble merkezlerini alip her birini orneklen
    5. En koyu (dolu) bubble'lari A/B/C/D/E olarak don
    6. Ogrenci no'yu da okunmus hanelerden birlestir

Kullanim:
    from app.omr.pipeline import omr_okuma
    result = omr_okuma(image_path='/tmp/ogr1.jpg',
                       soru_sayisi=120, sik_sayisi=5)
    # result.ogrenci_no, result.cevaplar, result.uyari

Tasarim notu: Kalibrasyon markerleri dolu siyah karelerdir; kontur alanina ve
"dikdortgensellige" (aspect-ratio) bakarak secilir. Pratikte fotograf hafif
egik/carpik cekildiyse perspektif donusumu tolere eder.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import numpy as np

from . import layout as L


# Perspektifle donusturulecek "hedef" tuval olcusu (mm basina N piksel)
PX_PER_MM = 5  # 210 mm * 5 = 1050 px; yeterli cozunurluk
WARP_W = int(L.PAGE_W_MM * PX_PER_MM)
WARP_H = int(L.PAGE_H_MM * PX_PER_MM)


@dataclass
class OmrSonuc:
    """OMR okuma sonucu."""
    ogrenci_no: Optional[str] = None
    # Soru no -> sik (A/B/C/D/E) veya None (bos)
    cevaplar: dict[int, Optional[str]] = field(default_factory=dict)
    uyari: List[str] = field(default_factory=list)
    basarili: bool = True
    hata: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps({
            'ogrenci_no': self.ogrenci_no,
            'cevaplar': [
                {'soru': k, 'cevap': v}
                for k, v in sorted(self.cevaplar.items())
            ],
            'uyari': self.uyari,
            'basarili': self.basarili,
            'hata': self.hata,
        }, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Marker tespiti + perspektif duzeltme
# ---------------------------------------------------------------------------

def _find_markers(gray: np.ndarray) -> Optional[np.ndarray]:
    """4 kose markerini bul — (4,2) kose nokta dizisi (TL, TR, BL, BR).

    None donerse marker bulunamadi demek.
    """
    h, w = gray.shape[:2]
    # Otsu threshold + invert (markerlar siyah -> beyaz olsun)
    _, th = cv2.threshold(gray, 0, 255,
                          cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # Kucuk gurultuyu temizle
    kernel = np.ones((3, 3), np.uint8)
    th = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    total_area = h * w
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 0.0005 * total_area or area > 0.02 * total_area:
            continue
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
        if len(approx) != 4:
            continue
        # Dikdortgen benzerligi: bounding box alani / kontur alani yaklasik 1
        x, y, bw, bh = cv2.boundingRect(approx)
        if bw == 0 or bh == 0:
            continue
        aspect = bw / float(bh)
        if aspect < 0.7 or aspect > 1.4:
            continue
        box_area = bw * bh
        if box_area > 0 and area / box_area < 0.7:
            continue
        cx, cy = x + bw / 2.0, y + bh / 2.0
        candidates.append((area, cx, cy, approx))

    if len(candidates) < 4:
        return None

    # En uygun 4 aday: her biri kagidin bir kosesine en yakin olan
    corners = {
        'TL': (0, 0),
        'TR': (w, 0),
        'BL': (0, h),
        'BR': (w, h),
    }
    chosen = {}
    for name, (tx, ty) in corners.items():
        best = None
        best_dist = float('inf')
        for cand in candidates:
            _, cx, cy, _ = cand
            d = (cx - tx) ** 2 + (cy - ty) ** 2
            if d < best_dist:
                best_dist = d
                best = cand
        chosen[name] = best

    # Ayni adayi iki kose icin sectiysek hatali
    ids = {id(v) for v in chosen.values()}
    if len(ids) < 4:
        return None

    pts = np.array([
        [chosen['TL'][1], chosen['TL'][2]],
        [chosen['TR'][1], chosen['TR'][2]],
        [chosen['BL'][1], chosen['BL'][2]],
        [chosen['BR'][1], chosen['BR'][2]],
    ], dtype=np.float32)
    return pts


def _warp_to_sheet(gray: np.ndarray, markers: np.ndarray) -> np.ndarray:
    """Markerlari kullanarak goruntuyu duz A4 tuvaline warp et."""
    # Hedef: mm olcekli sayfada markerlerin merkez koordinatlari (px)
    dst_pts = np.array([
        [L.MARKER_CENTERS_MM[0][0] * PX_PER_MM,
         L.MARKER_CENTERS_MM[0][1] * PX_PER_MM],
        [L.MARKER_CENTERS_MM[1][0] * PX_PER_MM,
         L.MARKER_CENTERS_MM[1][1] * PX_PER_MM],
        [L.MARKER_CENTERS_MM[2][0] * PX_PER_MM,
         L.MARKER_CENTERS_MM[2][1] * PX_PER_MM],
        [L.MARKER_CENTERS_MM[3][0] * PX_PER_MM,
         L.MARKER_CENTERS_MM[3][1] * PX_PER_MM],
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(markers, dst_pts)
    warped = cv2.warpPerspective(gray, M, (WARP_W, WARP_H),
                                 flags=cv2.INTER_LINEAR,
                                 borderValue=255)
    return warped


# ---------------------------------------------------------------------------
# Bubble orneklemesi
# ---------------------------------------------------------------------------

# Dolu/bos esigi: bubble icindeki koyuluk orani
FILL_THRESHOLD = 0.45   # bu oran ve uzeri "dolu" kabul edilir
AMBIGUITY_MARGIN = 0.10  # en dolu iki bubble arasi fark bu kadardan azsa supheli


def _mm_to_warp_px(x_mm: float, y_mm: float) -> Tuple[int, int]:
    return int(round(x_mm * PX_PER_MM)), int(round(y_mm * PX_PER_MM))


def _sample_bubble_fill(binary: np.ndarray, cx_px: int, cy_px: int,
                        r_mm: float) -> float:
    """Bubble'in icindeki doluluk oranini (0..1) dondur.

    binary: foreground = 255 (karanlik isaretler), background = 0.
    """
    r_px = max(1, int(round(r_mm * PX_PER_MM * 0.85)))  # biraz ici
    h, w = binary.shape
    x0, y0 = max(0, cx_px - r_px), max(0, cy_px - r_px)
    x1, y1 = min(w, cx_px + r_px + 1), min(h, cy_px + r_px + 1)
    patch = binary[y0:y1, x0:x1]
    if patch.size == 0:
        return 0.0
    # Dairesel maske
    yy, xx = np.ogrid[y0:y1, x0:x1]
    mask = (xx - cx_px) ** 2 + (yy - cy_px) ** 2 <= r_px ** 2
    if mask.sum() == 0:
        return 0.0
    filled = (patch[mask] > 0).sum()
    return filled / mask.sum()


def _read_ogrenci_no(binary: np.ndarray, uyari: list) -> Optional[str]:
    """Ogrenci no 8 haneli grid'ten oku."""
    digits = []
    for d in range(L.OGRENCI_NO_DIGITS):
        fills = []
        for v in range(L.OGRENCI_NO_ROWS):
            bc = L.ogrenci_no_bubble_center(d, v)
            cx, cy = _mm_to_warp_px(bc.x, bc.y)
            fr = _sample_bubble_fill(binary, cx, cy,
                                     L.OGRENCI_NO_BUBBLE_R_MM)
            fills.append(fr)
        max_fr = max(fills)
        if max_fr < FILL_THRESHOLD:
            digits.append(' ')  # bos hane
            continue
        idx = fills.index(max_fr)
        # Ikinci en dolu ile fark
        fills_sorted = sorted(fills, reverse=True)
        if len(fills_sorted) > 1 and (fills_sorted[0] - fills_sorted[1]) < AMBIGUITY_MARGIN:
            uyari.append(f'Ogrenci no hane {d + 1}: belirsiz isaret')
        digits.append(str(idx))
    # Bos haneleri kirparak numara
    s = ''.join(digits).strip()
    return s if s else None


def _read_answers(binary: np.ndarray, soru_sayisi: int, sik_sayisi: int,
                  uyari: list) -> dict[int, Optional[str]]:
    """Cevap bubble'larini oku."""
    cevaplar: dict[int, Optional[str]] = {}
    for q in range(1, soru_sayisi + 1):
        fills = []
        for i in range(sik_sayisi):
            bc = L.answer_bubble_center(q, i)
            cx, cy = _mm_to_warp_px(bc.x, bc.y)
            fr = _sample_bubble_fill(binary, cx, cy, L.BUBBLE_R_MM)
            fills.append(fr)
        max_fr = max(fills)
        if max_fr < FILL_THRESHOLD:
            cevaplar[q] = None  # bos
            continue
        # Cift isaret kontrolu: iki bubble da esigin uzerindeyse yanlis sayilsin
        above = [i for i, f in enumerate(fills) if f >= FILL_THRESHOLD]
        if len(above) > 1:
            uyari.append(f'Soru {q}: cift isaret, bos sayildi')
            cevaplar[q] = None
            continue
        idx = fills.index(max_fr)
        # Belirsizlik uyarisi
        fills_sorted = sorted(fills, reverse=True)
        if (fills_sorted[0] - fills_sorted[1]) < AMBIGUITY_MARGIN:
            uyari.append(f'Soru {q}: belirsiz isaret (sec={L.ANSWER_OPTIONS[idx]})')
        cevaplar[q] = L.ANSWER_OPTIONS[idx]
    return cevaplar


# ---------------------------------------------------------------------------
# Ana API
# ---------------------------------------------------------------------------

def _load_image(image_path: Optional[str],
                image_bytes: Optional[bytes]) -> Optional[np.ndarray]:
    if image_path:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        return img
    if image_bytes:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
        return img
    return None


def omr_okuma(image_path: Optional[str] = None,
              image_bytes: Optional[bytes] = None,
              soru_sayisi: int = L.MAX_QUESTIONS,
              sik_sayisi: int = L.N_OPTIONS) -> OmrSonuc:
    """Cevap kagidi fotografini oku, OmrSonuc dondur."""
    gray = _load_image(image_path, image_bytes)
    if gray is None:
        return OmrSonuc(basarili=False,
                        hata='Goruntu yuklenemedi (gecersiz dosya veya bytes).')

    # Goruntu cok buyukse kuculterek isle
    h, w = gray.shape[:2]
    max_dim = 2000
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        gray = cv2.resize(gray, (int(w * scale), int(h * scale)),
                          interpolation=cv2.INTER_AREA)

    # Hafif blur ile gurultu azalt
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    markers = _find_markers(blurred)
    if markers is None:
        return OmrSonuc(basarili=False,
                        hata='Kalibrasyon marker bulunamadi (4 kose).')

    warped = _warp_to_sheet(gray, markers)

    # Adaptive threshold — isaretli bubble'lar beyaz olacak sekilde
    warp_blurred = cv2.GaussianBlur(warped, (5, 5), 0)
    binary = cv2.adaptiveThreshold(
        warp_blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 21, 8
    )

    uyari: list = []
    ogrenci_no = _read_ogrenci_no(binary, uyari)
    cevaplar = _read_answers(binary, min(soru_sayisi, L.MAX_QUESTIONS),
                             min(sik_sayisi, L.N_OPTIONS), uyari)

    return OmrSonuc(
        ogrenci_no=ogrenci_no,
        cevaplar=cevaplar,
        uyari=uyari,
        basarili=True,
    )


# ---------------------------------------------------------------------------
# Cevap anahtariyla karsilastirma
# ---------------------------------------------------------------------------

def karsilastir(cevaplar: dict[int, Optional[str]],
                anahtar: dict[int, str],
                iptal: Optional[set[int]] = None) -> dict:
    """Ogrencinin cevaplari vs anahtar — D/Y/B dokumu dondur.

    iptal: cevabi ne olursa olsun dogru sayilacak soru numaralari.
    """
    iptal = iptal or set()
    dogru = yanlis = bos = 0
    detay = []
    for q in sorted(anahtar.keys()):
        if q in iptal:
            dogru += 1
            detay.append({'soru': q, 'durum': 'iptal-dogru',
                          'ogrenci': cevaplar.get(q), 'anahtar': anahtar[q]})
            continue
        verilen = cevaplar.get(q)
        if verilen is None:
            bos += 1
            detay.append({'soru': q, 'durum': 'bos',
                          'ogrenci': None, 'anahtar': anahtar[q]})
        elif verilen == anahtar[q]:
            dogru += 1
            detay.append({'soru': q, 'durum': 'dogru',
                          'ogrenci': verilen, 'anahtar': anahtar[q]})
        else:
            yanlis += 1
            detay.append({'soru': q, 'durum': 'yanlis',
                          'ogrenci': verilen, 'anahtar': anahtar[q]})
    net = round(dogru - yanlis / 4.0, 2)
    return {
        'dogru': dogru,
        'yanlis': yanlis,
        'bos': bos,
        'net': net,
        'detay': detay,
    }
