"""Test amacli: layout sabitlerini kullanarak 'isaretli' dummy bir cevap kagidi
goruntusu uretir. OMR pipeline'ini gercek fotograf aramadan dogrulamak icin.

Kullanim:
    from app.omr.tests.render_dummy import render_synthetic_sheet
    img = render_synthetic_sheet(
        cevaplar={1: 'A', 2: 'C', 3: 'E', ...},
        ogrenci_no='12345678',
    )
    cv2.imwrite('/tmp/synthetic.png', img)
"""
from typing import Optional

import cv2
import numpy as np

from .. import layout as L
from ..pipeline import PX_PER_MM, WARP_W, WARP_H


def render_synthetic_sheet(
    cevaplar: dict[int, str],
    ogrenci_no: Optional[str] = None,
    noise: bool = False,
    rotate_deg: float = 0.0,
) -> np.ndarray:
    """Synthetic cevap kagidi goruntusu uret (grayscale, 0-255).

    - `cevaplar`: {soru_no: 'A'|'B'|...} — isaretlenecek cevaplar
    - `ogrenci_no`: 1-8 haneli str; eksik haneler bos birakilir
    - `noise`: hafif gurultu ekle (gercekciligi artirir)
    - `rotate_deg`: sayfayi bu kadar dondur (perspektif testi)
    """
    # Beyaz tuval
    img = np.full((WARP_H, WARP_W), 255, dtype=np.uint8)

    # Kalibrasyon markerleri (dolu siyah kareler)
    sz = int(L.MARKER_SIZE_MM * PX_PER_MM)
    for cx, cy in L.MARKER_CENTERS_MM:
        x_px = int(cx * PX_PER_MM - sz / 2)
        y_px = int(cy * PX_PER_MM - sz / 2)
        cv2.rectangle(img, (x_px, y_px), (x_px + sz, y_px + sz), 0, -1)

    # Bubble cercevesi (hafif ince gri) — gercek sablonu taklit
    def _draw_empty_bubble(cx_mm: float, cy_mm: float, r_mm: float) -> None:
        cx_px = int(round(cx_mm * PX_PER_MM))
        cy_px = int(round(cy_mm * PX_PER_MM))
        r_px = max(1, int(round(r_mm * PX_PER_MM)))
        cv2.circle(img, (cx_px, cy_px), r_px, 180, 1)

    def _fill_bubble(cx_mm: float, cy_mm: float, r_mm: float) -> None:
        cx_px = int(round(cx_mm * PX_PER_MM))
        cy_px = int(round(cy_mm * PX_PER_MM))
        r_px = max(1, int(round(r_mm * PX_PER_MM * 0.85)))
        cv2.circle(img, (cx_px, cy_px), r_px, 30, -1)  # koyu gri, "dolu"

    # Ogrenci no bubble'lari
    for d in range(L.OGRENCI_NO_DIGITS):
        for v in range(L.OGRENCI_NO_ROWS):
            bc = L.ogrenci_no_bubble_center(d, v)
            _draw_empty_bubble(bc.x, bc.y, L.OGRENCI_NO_BUBBLE_R_MM)
    if ogrenci_no:
        for d, ch in enumerate(ogrenci_no[:L.OGRENCI_NO_DIGITS]):
            if ch.isdigit():
                bc = L.ogrenci_no_bubble_center(d, int(ch))
                _fill_bubble(bc.x, bc.y, L.OGRENCI_NO_BUBBLE_R_MM)

    # Cevap bubble'lari
    for q in range(1, L.MAX_QUESTIONS + 1):
        for i in range(L.N_OPTIONS):
            bc = L.answer_bubble_center(q, i)
            _draw_empty_bubble(bc.x, bc.y, L.BUBBLE_R_MM)

    # Isaretlenen cevaplar
    for q, ch in cevaplar.items():
        if ch not in L.ANSWER_OPTIONS:
            continue
        idx = L.ANSWER_OPTIONS.index(ch)
        bc = L.answer_bubble_center(q, idx)
        _fill_bubble(bc.x, bc.y, L.BUBBLE_R_MM)

    if noise:
        noise_arr = np.random.normal(0, 10, img.shape).astype(np.int16)
        img = np.clip(img.astype(np.int16) + noise_arr, 0, 255).astype(np.uint8)

    if rotate_deg != 0.0:
        center = (WARP_W / 2, WARP_H / 2)
        M = cv2.getRotationMatrix2D(center, rotate_deg, 1.0)
        img = cv2.warpAffine(img, M, (WARP_W, WARP_H),
                             flags=cv2.INTER_LINEAR,
                             borderValue=255)

    return img
