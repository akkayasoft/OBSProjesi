"""Toplu yukleme (Excel import) yardimci fonksiyonlari."""
from datetime import date, datetime
from io import BytesIO
from decimal import Decimal, InvalidOperation


def excel_sablonu_olustur(basliklar, ornek_satirlar=None, aciklama_satiri=None, sayfa_adi='Veri'):
    """Verilen basliklarla Excel sablonu olusturur.

    basliklar: list[dict] — her biri {'key': 'ogrenci_no', 'label': 'Öğrenci No', 'zorunlu': True, 'ornek': '1001'}
    ornek_satirlar: list[list] — basliklar sirasina uygun ornek veri satirlari
    aciklama_satiri: ilk satira yazilacak kullanici aciklamasi (istege bagli)
    """
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = sayfa_adi

    thin = Side(border_style='thin', color='CCCCCC')
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    baslangic_satir = 1
    if aciklama_satiri:
        ws.cell(row=1, column=1, value=aciklama_satiri)
        ws.cell(row=1, column=1).font = Font(italic=True, color='666666', size=10)
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(basliklar))
        baslangic_satir = 2

    # Basliklar
    header_fill = PatternFill('solid', fgColor='2F6DB5')
    header_font = Font(bold=True, color='FFFFFF', size=11)
    zorunlu_fill = PatternFill('solid', fgColor='D93A3A')

    for idx, b in enumerate(basliklar, start=1):
        cell = ws.cell(row=baslangic_satir, column=idx, value=b['label'] + (' *' if b.get('zorunlu') else ''))
        cell.font = header_font
        cell.fill = header_fill if not b.get('zorunlu') else zorunlu_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = border

        # Kolon genisligi
        ws.column_dimensions[get_column_letter(idx)].width = max(len(b['label']) + 4, 15)

    ws.row_dimensions[baslangic_satir].height = 30

    # Ornek satirlar
    if ornek_satirlar:
        for r_idx, satir in enumerate(ornek_satirlar, start=baslangic_satir + 1):
            for c_idx, val in enumerate(satir, start=1):
                c = ws.cell(row=r_idx, column=c_idx, value=val)
                c.border = border
                c.font = Font(italic=True, color='888888')

    # Donen: BytesIO
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output


def excel_oku(dosya, basliklar, baslangic_satir=2):
    """Yuklenen Excel dosyasini parse eder.

    basliklar: excel_sablonu_olustur ile ayni format
    baslangic_satir: veri satirlarinin basladigi satir (aciklama varsa 3, yoksa 2)

    Donus: list[dict] — her biri key -> deger map'i, ek olarak '_satir_no' ve '_hatalar' alanlari
    """
    from openpyxl import load_workbook

    wb = load_workbook(dosya, data_only=True)
    ws = wb.active

    # Baslik satirini bul (aciklama satiri var mi?)
    baslik_satir_no = None
    for r in range(1, 4):
        row_vals = [str(ws.cell(row=r, column=c).value or '').replace(' *', '').strip()
                    for c in range(1, len(basliklar) + 1)]
        expected = [b['label'] for b in basliklar]
        # En az ilk 3 basligin eslesmesi yeterli
        match = sum(1 for a, e in zip(row_vals, expected) if a == e)
        if match >= min(3, len(basliklar)):
            baslik_satir_no = r
            break

    if baslik_satir_no is None:
        raise ValueError(
            'Şablon başlıkları bulunamadı. Lütfen indirilen şablonu kullanın ve '
            'başlık satırını değiştirmeyin.'
        )

    satirlar = []
    for r in range(baslik_satir_no + 1, ws.max_row + 1):
        satir = {'_satir_no': r, '_hatalar': []}
        hepsi_bos = True

        for idx, b in enumerate(basliklar, start=1):
            val = ws.cell(row=r, column=idx).value
            if val is not None and str(val).strip() != '':
                hepsi_bos = False
            satir[b['key']] = val

        if hepsi_bos:
            continue

        satirlar.append(satir)

    return satirlar


def dogrula_str(val, zorunlu=False, max_len=None, label=''):
    """String degeri dogrular, hata listesi doner."""
    if val is None or str(val).strip() == '':
        if zorunlu:
            return None, f'{label} zorunludur.'
        return None, None
    s = str(val).strip()
    if max_len and len(s) > max_len:
        return None, f'{label} en fazla {max_len} karakter olabilir.'
    return s, None


def dogrula_sayi(val, zorunlu=False, min_val=None, max_val=None, tam_sayi=False, label=''):
    if val is None or str(val).strip() == '':
        if zorunlu:
            return None, f'{label} zorunludur.'
        return None, None
    try:
        if tam_sayi:
            n = int(float(str(val).replace(',', '.').strip()))
        else:
            n = Decimal(str(val).replace(',', '.').strip())
    except (ValueError, InvalidOperation):
        return None, f'{label} geçerli bir sayı olmalı.'

    if min_val is not None and n < min_val:
        return None, f'{label} en az {min_val} olmalı.'
    if max_val is not None and n > max_val:
        return None, f'{label} en fazla {max_val} olabilir.'
    return n, None


def dogrula_tarih(val, zorunlu=False, label=''):
    if val is None or (isinstance(val, str) and val.strip() == ''):
        if zorunlu:
            return None, f'{label} zorunludur.'
        return None, None
    if isinstance(val, datetime):
        return val.date(), None
    if isinstance(val, date):
        return val, None
    # String olarak gelmisse parse
    for fmt in ('%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            return datetime.strptime(str(val).strip(), fmt).date(), None
        except ValueError:
            continue
    return None, f'{label} gecerli bir tarih olmalı (YYYY-MM-DD veya DD.MM.YYYY).'
