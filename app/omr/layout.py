"""OMR optik form sablon layout sabitleri.

Tum olculer **milimetre** cinsindendir. A4 portrait kagit varsayar.
PDF uretici (pdf_template.py) ve OMR pipeline (pipeline.py) ayni sabitleri
paylasir — boylece yazdirilan form ile okuyan algoritma uyumlu kalir.

Genel mantik:
- 4 kose kalibrasyon markeri (siyah dolu kareler): perspektif duzeltme
- Ust kisim: okul/sinav basligi + ogrenci adi + ogrenci no bubble grid
- Orta/alt kisim: 4 sutunlu cevap gridi (her satir bir soru, 5 sik)

Max 120 soru / 8 haneli ogrenci no destekler.
Ogrenciler LGS icin 4 sik, TYT/AYT icin 5 sik isaretleyebilir; bos kolonlar
sablonda yine cizilir ama OMR okumada kullanilmayabilir.
"""
from dataclasses import dataclass

# ---- Sayfa ------------------------------------------------------------------
PAGE_W_MM = 210.0
PAGE_H_MM = 297.0

# ---- Kose marker -----------------------------------------------------------
# Siyah dolu kareler. OMR perspektif duzeltme icin 4 kosede aranir.
MARKER_SIZE_MM = 8.0
MARKER_MARGIN_MM = 8.0  # Kagit kenarina uzaklik (marker'in disi)

# Marker merkez koordinatlari (TL, TR, BL, BR) — mm cinsinden
MARKER_CENTERS_MM = [
    (MARKER_MARGIN_MM + MARKER_SIZE_MM / 2,
     MARKER_MARGIN_MM + MARKER_SIZE_MM / 2),                              # TL
    (PAGE_W_MM - MARKER_MARGIN_MM - MARKER_SIZE_MM / 2,
     MARKER_MARGIN_MM + MARKER_SIZE_MM / 2),                              # TR
    (MARKER_MARGIN_MM + MARKER_SIZE_MM / 2,
     PAGE_H_MM - MARKER_MARGIN_MM - MARKER_SIZE_MM / 2),                  # BL
    (PAGE_W_MM - MARKER_MARGIN_MM - MARKER_SIZE_MM / 2,
     PAGE_H_MM - MARKER_MARGIN_MM - MARKER_SIZE_MM / 2),                  # BR
]

# Icerik alani (markerlarin ic kenari arasi)
CONTENT_X0_MM = MARKER_MARGIN_MM + MARKER_SIZE_MM + 4.0
CONTENT_Y0_MM = MARKER_MARGIN_MM + MARKER_SIZE_MM + 4.0
CONTENT_X1_MM = PAGE_W_MM - (MARKER_MARGIN_MM + MARKER_SIZE_MM + 4.0)
CONTENT_Y1_MM = PAGE_H_MM - (MARKER_MARGIN_MM + MARKER_SIZE_MM + 4.0)

# ---- Header blogu (basliklar + ogrenci bilgisi) ----------------------------
HEADER_HEIGHT_MM = 55.0  # content alaninin ust kismindan ayrilan

# Ogrenci No bubble grid: 8 sutun, 0-9 arasi dolu kareler
OGRENCI_NO_DIGITS = 8
OGRENCI_NO_ROWS = 10          # 0..9
OGRENCI_NO_BUBBLE_R_MM = 1.6  # yaricap
OGRENCI_NO_COL_STEP_MM = 6.0  # sutunlar arasi
OGRENCI_NO_ROW_STEP_MM = 4.0  # satirlar arasi
# Grid sol-ust kosesi (ilk bubble merkezi)
OGRENCI_NO_X0_MM = CONTENT_X0_MM + 40.0  # Sol tarafta ad-soyad alani birakiyoruz
OGRENCI_NO_Y0_MM = CONTENT_Y0_MM + 12.0

# ---- Cevap gridi -----------------------------------------------------------
ANSWER_COLUMNS = 4        # 4 sutun
ANSWER_ROWS_PER_COL = 30  # her sutunda 30 soru
MAX_QUESTIONS = ANSWER_COLUMNS * ANSWER_ROWS_PER_COL  # 120
ANSWER_OPTIONS = ['A', 'B', 'C', 'D', 'E']
N_OPTIONS = len(ANSWER_OPTIONS)

BUBBLE_R_MM = 2.0
OPT_STEP_MM = 5.5            # A-B, B-C, ... merkezleri arasi
ROW_STEP_MM = 7.0            # satirlar arasi
COL_STEP_MM = 42.0           # sutunlar arasi (soru_no kolonu hizi)
QLABEL_OFFSET_MM = 5.0       # soru_no bubble'larin solunda
FIRST_BUBBLE_OFFSET_MM = 8.0  # soru_no solunda bosluk, sonra A

# Cevap gridinin sol-ust kosesi (ilk soru'nun soru numarasi baslangici)
GRID_X0_MM = CONTENT_X0_MM + 2.0
GRID_Y0_MM = CONTENT_Y0_MM + HEADER_HEIGHT_MM


@dataclass
class BubbleCoord:
    """Bir bubble'in mm cinsinden merkez koordinati."""
    x: float
    y: float


def answer_bubble_center(soru_no: int, option_idx: int) -> BubbleCoord:
    """Belirli sorunun belirli sikki icin bubble merkezi (mm)."""
    if not 1 <= soru_no <= MAX_QUESTIONS:
        raise ValueError(f'soru_no 1..{MAX_QUESTIONS} araliginda olmali')
    if not 0 <= option_idx < N_OPTIONS:
        raise ValueError(f'option_idx 0..{N_OPTIONS - 1} araliginda olmali')
    col = (soru_no - 1) // ANSWER_ROWS_PER_COL
    row = (soru_no - 1) % ANSWER_ROWS_PER_COL
    x = GRID_X0_MM + col * COL_STEP_MM + FIRST_BUBBLE_OFFSET_MM + option_idx * OPT_STEP_MM
    y = GRID_Y0_MM + row * ROW_STEP_MM
    return BubbleCoord(x=x, y=y)


def question_label_pos(soru_no: int) -> BubbleCoord:
    """Soru numarasi metninin bulunmasi gereken konum (sag-alt baz)."""
    col = (soru_no - 1) // ANSWER_ROWS_PER_COL
    row = (soru_no - 1) % ANSWER_ROWS_PER_COL
    x = GRID_X0_MM + col * COL_STEP_MM
    y = GRID_Y0_MM + row * ROW_STEP_MM
    return BubbleCoord(x=x, y=y)


def ogrenci_no_bubble_center(digit_idx: int, value: int) -> BubbleCoord:
    """Ogrenci no: digit_idx. hanenin `value` (0-9) bubble merkezi."""
    if not 0 <= digit_idx < OGRENCI_NO_DIGITS:
        raise ValueError('digit_idx 0..7')
    if not 0 <= value <= 9:
        raise ValueError('value 0..9')
    x = OGRENCI_NO_X0_MM + digit_idx * OGRENCI_NO_COL_STEP_MM
    y = OGRENCI_NO_Y0_MM + value * OGRENCI_NO_ROW_STEP_MM
    return BubbleCoord(x=x, y=y)


# mm -> nokta donusumu (reportlab points, 1 pt = 1/72 inch, 1 inch = 25.4 mm)
def mm_to_pt(mm: float) -> float:
    return mm * 72.0 / 25.4
