import json
from collections import Counter
from flask import Blueprint, render_template
from flask_login import login_required
from app.utils import role_required
from app.models.anket import Anket, AnketSoru, AnketCevap
from app.extensions import db

bp = Blueprint('sonuc', __name__)


@bp.route('/<int:anket_id>')
@login_required
@role_required('admin', 'ogretmen')
def goruntule(anket_id):
    anket = Anket.query.get_or_404(anket_id)
    sorular = anket.sorular.order_by(AnketSoru.sira).all()

    # Her soru icin sonuclari hesapla
    sonuclar = []
    for soru in sorular:
        cevaplar = AnketCevap.query.filter(
            AnketCevap.soru_id == soru.id,
            AnketCevap.cevap != '__katilim_isaretci__',
        ).all()

        soru_sonuc = {
            'soru': soru,
            'toplam_cevap': len(cevaplar),
            'cevaplar': cevaplar,
        }

        if soru.soru_tipi in ('coktan_secmeli', 'evet_hayir'):
            # Seceneklere gore dagalim
            sayac = Counter(c.cevap for c in cevaplar)
            if soru.soru_tipi == 'evet_hayir':
                secenekler = ['Evet', 'Hayir']
            else:
                secenekler = soru.secenekler_listesi

            dagilim = []
            for secenek in secenekler:
                sayi = sayac.get(secenek, 0)
                oran = (sayi / len(cevaplar) * 100) if cevaplar else 0
                dagilim.append({
                    'secenek': secenek,
                    'sayi': sayi,
                    'oran': round(oran, 1),
                })
            soru_sonuc['dagilim'] = dagilim
            soru_sonuc['chart_labels'] = json.dumps([d['secenek'] for d in dagilim], ensure_ascii=False)
            soru_sonuc['chart_data'] = json.dumps([d['sayi'] for d in dagilim])

        elif soru.soru_tipi == 'derecelendirme':
            sayac = Counter(c.cevap for c in cevaplar)
            dagilim = []
            for i in range(1, 6):
                sayi = sayac.get(str(i), 0)
                oran = (sayi / len(cevaplar) * 100) if cevaplar else 0
                dagilim.append({
                    'secenek': str(i),
                    'sayi': sayi,
                    'oran': round(oran, 1),
                })
            soru_sonuc['dagilim'] = dagilim
            soru_sonuc['chart_labels'] = json.dumps([str(i) for i in range(1, 6)])
            soru_sonuc['chart_data'] = json.dumps([d['sayi'] for d in dagilim])

            # Ortalama hesapla
            if cevaplar:
                toplam = sum(int(c.cevap) for c in cevaplar if c.cevap.isdigit())
                soru_sonuc['ortalama'] = round(toplam / len(cevaplar), 2)
            else:
                soru_sonuc['ortalama'] = 0

        elif soru.soru_tipi == 'acik_uclu':
            soru_sonuc['yanitlar'] = [c.cevap for c in cevaplar]

        sonuclar.append(soru_sonuc)

    katilimci_sayisi = anket.katilimci_sayisi

    return render_template('anket/sonuc.html',
                           anket=anket,
                           sonuclar=sonuclar,
                           katilimci_sayisi=katilimci_sayisi)
