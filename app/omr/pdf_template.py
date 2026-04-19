"""Optik cevap kagidi PDF sablonu uretici (reportlab).

Kullanim:
    from app.omr.pdf_template import generate_answer_sheet_pdf
    generate_answer_sheet_pdf(
        sinav_adi='TYT Genel Deneme #4',
        ders_bilgisi='Turkce 40 / Sosyal 20 / Mat 40 / Fen 20',
        output_path='/tmp/sheet.pdf',
        soru_sayisi=120,
        sik_sayisi=5,
    )

Uretilen PDF'in 4 kosesinde siyah kalibrasyon markerleri vardir; OMR
pipeline'i bu markerlari bulup perspektif duzeltme uygular, ardindan
layout.py'deki sabit koordinatlardan bubble'lari okur.
"""
from io import BytesIO
from typing import Optional

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

from . import layout as L


def _draw_markers(c: canvas.Canvas) -> None:
    """4 kose dolu siyah kareleri ciz."""
    c.setFillColorRGB(0, 0, 0)
    size = L.MARKER_SIZE_MM * mm
    for cx, cy in L.MARKER_CENTERS_MM:
        # reportlab koordinat sistemi: y alttan baslar -> cevirelim
        x_pt = cx * mm - size / 2
        y_pt = (L.PAGE_H_MM - cy) * mm - size / 2
        c.rect(x_pt, y_pt, size, size, stroke=0, fill=1)


def _mm_xy(x_mm: float, y_mm: float) -> tuple[float, float]:
    """mm (top-left origin) -> reportlab pt (bottom-left origin)."""
    return x_mm * mm, (L.PAGE_H_MM - y_mm) * mm


def _draw_header(c: canvas.Canvas, sinav_adi: str, ders_bilgisi: str) -> None:
    """Ust blok: baslik + ad-soyad cizgisi + ogrenci no bubble grid."""
    # Baslik
    c.setFont('Helvetica-Bold', 14)
    x_pt, y_pt = _mm_xy(L.CONTENT_X0_MM + 2, L.CONTENT_Y0_MM + 5)
    c.drawString(x_pt, y_pt, sinav_adi[:80])

    c.setFont('Helvetica', 9)
    x_pt, y_pt = _mm_xy(L.CONTENT_X0_MM + 2, L.CONTENT_Y0_MM + 10)
    c.drawString(x_pt, y_pt, ders_bilgisi[:120])

    # Ad-Soyad cizgisi
    c.setFont('Helvetica', 9)
    x_pt, y_pt = _mm_xy(L.CONTENT_X0_MM + 2, L.CONTENT_Y0_MM + 20)
    c.drawString(x_pt, y_pt, 'Ad-Soyad: ____________________________')

    x_pt, y_pt = _mm_xy(L.CONTENT_X0_MM + 2, L.CONTENT_Y0_MM + 28)
    c.drawString(x_pt, y_pt, 'Sube: ______________')

    x_pt, y_pt = _mm_xy(L.CONTENT_X0_MM + 2, L.CONTENT_Y0_MM + 36)
    c.drawString(x_pt, y_pt, 'Tarih: ____/____/______')

    # Ogrenci No bubble grid
    c.setFont('Helvetica-Bold', 8)
    x_pt, y_pt = _mm_xy(L.OGRENCI_NO_X0_MM - 2,
                        L.OGRENCI_NO_Y0_MM - 5)
    c.drawString(x_pt, y_pt, 'OGRENCI NO')

    # Hane etiketleri (1..8)
    c.setFont('Helvetica', 7)
    for d in range(L.OGRENCI_NO_DIGITS):
        center = L.ogrenci_no_bubble_center(d, 0)
        x_pt, y_pt = _mm_xy(center.x, L.OGRENCI_NO_Y0_MM - 2)
        c.drawCentredString(x_pt, y_pt, str(d + 1))

    # Bubble'lar
    c.setLineWidth(0.5)
    for d in range(L.OGRENCI_NO_DIGITS):
        for v in range(L.OGRENCI_NO_ROWS):
            center = L.ogrenci_no_bubble_center(d, v)
            x_pt, y_pt = _mm_xy(center.x, center.y)
            c.circle(x_pt, y_pt, L.OGRENCI_NO_BUBBLE_R_MM * mm,
                     stroke=1, fill=0)
            # Rakamlari bubble icine yaz (kucuk font)
            c.setFont('Helvetica', 4.5)
            c.drawCentredString(x_pt, y_pt - 1.3, str(v))


def _draw_answer_grid(c: canvas.Canvas, soru_sayisi: int,
                      sik_sayisi: int) -> None:
    """Cevap bubble grid."""
    soru_sayisi = min(soru_sayisi, L.MAX_QUESTIONS)
    sik_sayisi = min(sik_sayisi, L.N_OPTIONS)

    c.setLineWidth(0.5)
    for q in range(1, soru_sayisi + 1):
        # Soru numarasi etiketi (soldaki)
        qlabel = L.question_label_pos(q)
        x_pt, y_pt = _mm_xy(qlabel.x, qlabel.y + 0.5)
        c.setFont('Helvetica-Bold', 7)
        c.drawString(x_pt, y_pt, f'{q:>3}.')

        for i in range(sik_sayisi):
            bc = L.answer_bubble_center(q, i)
            x_pt, y_pt = _mm_xy(bc.x, bc.y)
            c.circle(x_pt, y_pt, L.BUBBLE_R_MM * mm, stroke=1, fill=0)
            # Sik harfi bubble icinde
            c.setFont('Helvetica', 5)
            c.drawCentredString(x_pt, y_pt - 1.5, L.ANSWER_OPTIONS[i])


def generate_answer_sheet_pdf(
    sinav_adi: str,
    ders_bilgisi: str,
    soru_sayisi: int = L.MAX_QUESTIONS,
    sik_sayisi: int = L.N_OPTIONS,
    output_path: Optional[str] = None,
) -> bytes:
    """Optik cevap kagidi PDF'i uret.

    Eger `output_path` verilirse dosyaya yazar; ayrica daima PDF bytes'i
    doner (Flask download icin kullanisli).
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f'OMR Optik Form - {sinav_adi}')

    _draw_markers(c)
    _draw_header(c, sinav_adi, ders_bilgisi)
    _draw_answer_grid(c, soru_sayisi, sik_sayisi)

    # Alt bilgi
    c.setFont('Helvetica-Oblique', 6)
    x_pt, y_pt = _mm_xy(L.CONTENT_X0_MM + 2, L.CONTENT_Y1_MM - 1)
    c.drawString(x_pt, y_pt,
                 f'Sadece 2B/HB kursun kalem ile bubble\'lari tamamen doldurun. '
                 f'Max soru: {soru_sayisi}')

    c.showPage()
    c.save()

    pdf_bytes = buf.getvalue()
    buf.close()

    if output_path:
        with open(output_path, 'wb') as f:
            f.write(pdf_bytes)

    return pdf_bytes
