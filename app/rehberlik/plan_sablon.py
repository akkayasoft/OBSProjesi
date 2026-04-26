"""Risk skoruna gore otomatik rehberlik plani sablonu uretici.

Yeni plan acilirken ogrencinin risk sinyallerine bakip uygun bir sablon
secer ve baslik / hedefler / uygulanacak yontemleri onceden doldurur.
Rehber ogretmen sablon ustunde duzenleyerek son halini verir.

Kullanim:
    from app.rehberlik.plan_sablon import plan_sablonu_uret
    sablon = plan_sablonu_uret(ogrenci_id)

Cikti:
    {
        'ogrenci': Ogrenci | None,
        'risk': dict,                      # ogrenci_risk_skoru ciktisi
        'sablon_kodu': str,                # 'akademik' | 'devamsizlik' | 'davranis' | 'kapsamli' | 'genel'
        'sablon_ad': str,
        'baslik': str,
        'hedefler': str,                   # multi-line text, textarea'a hazir
        'uygulanacak_yontemler': str,
        'baslangic_tarihi': date,
        'bitis_tarihi': date,
        'gerekce': list[str],              # neden bu sablon secildi
    }
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.models.muhasebe import Ogrenci
from app.rehberlik.risk_skoru import ogrenci_risk_skoru


VARSAYILAN_SURE_GUN = 56  # 8 hafta


# --- Sablonlar ------------------------------------------------------------
# Her sablon: kod -> {ad, baslik_format, hedefler, yontemler}

SABLONLAR: dict[str, dict[str, Any]] = {
    'akademik': {
        'ad': 'Akademik Destek Plani',
        'baslik_format': '{ogrenci_ad} - Akademik Destek ve Calisma Plani',
        'hedefler': (
            "1. Onumuzdeki 8 haftada deneme sinavi puaninda en az %10 artis saglamak.\n"
            "2. En zayif iki dersi tespit edip haftalik etut programina dahil etmek.\n"
            "3. Haftalik calisma takvimi olusturmak ve haftalik kontrol toplantisi yapmak.\n"
            "4. Hedef bolum/seviye ile mevcut performans arasindaki farki gostermek; somut "
            "ara hedefler belirlemek."
        ),
        'uygulanacak_yontemler': (
            "- Haftalik 30 dakikalik bireysel takip gorusmesi (calisma plani kontrolu).\n"
            "- Zayif derslerde branş ogretmeniyle koordinasyonla ek etut planlanmasi.\n"
            "- Calisma kaynaklarinin gozden gecirilmesi; soru bankasi ve konu anlatim "
            "materyali onerileri.\n"
            "- Deneme sinavi sonrasi puan analizinin ogrenciyle birlikte yapilmasi.\n"
            "- Veliyle 2 haftalik aralarla bilgilendirme."
        ),
    },
    'devamsizlik': {
        'ad': 'Devamsizlik Takip Plani',
        'baslik_format': '{ogrenci_ad} - Devamsizlik Takip ve Iyilestirme Plani',
        'hedefler': (
            "1. Onumuzdeki 8 haftada okula devam orani %95 ve uzerine cikarilmasi.\n"
            "2. Devamsizlik nedenlerinin (saglik, motivasyon, ulasim, aile vb.) "
            "belirlenmesi ve uygun destegin saglanmasi.\n"
            "3. Devamsizligin akademik basariya etkisinin ogrenciyle birlikte "
            "degerlendirilmesi."
        ),
        'uygulanacak_yontemler': (
            "- Ogrenciyle bireysel gorusme: devamsizlik nedenleri uzerine.\n"
            "- Veliyle yuz yuze gorusme planlanmasi.\n"
            "- Gunluk devam takibinin sinif ogretmeni / okul yonetimi ile birlikte "
            "yurutulmesi.\n"
            "- Devamsizlik ardindan telafi calismasi onerilmesi.\n"
            "- 3 hafta sonunda durum degerlendirmesi yapilarak plan revizyonu."
        ),
    },
    'davranis': {
        'ad': 'Davranissal Destek Plani',
        'baslik_format': '{ogrenci_ad} - Davranissal Destek Plani',
        'hedefler': (
            "1. Olumsuz davranis kayit sayisinin onumuzdeki 8 haftada en az "
            "yariya inmesi.\n"
            "2. Sinif ici sosyal etkilesim becerilerinin gelistirilmesi.\n"
            "3. Olumsuz davranisin altinda yatan faktorlerin (akran iliskileri, aile, "
            "akademik basari kaygisi vb.) anlasilmasi."
        ),
        'uygulanacak_yontemler': (
            "- Haftalik bireysel rehberlik gorusmesi.\n"
            "- Davranis sozlesmesi: ogrenciyle birlikte hedef davranislarin "
            "belirlenmesi ve takibi.\n"
            "- Olumlu pekistirme: hedeflere ulasildiginda olumlu geri bildirim.\n"
            "- Sinif ogretmenleri ile koordinasyonla tutarli yaklasim saglanmasi.\n"
            "- Gerektiginde grup gorusmesi veya sosyal beceri etkinligi."
        ),
    },
    'kapsamli': {
        'ad': 'Kapsamli Erken Uyari Plani',
        'baslik_format': '{ogrenci_ad} - Kapsamli Rehberlik ve Destek Plani',
        'hedefler': (
            "1. Akademik, davranissal ve devam alanlarinda butuncul iyilesme saglanmasi.\n"
            "2. Risk skorunun onumuzdeki 8 haftada 'orta' ya da 'dusuk' seviyeye cekilmesi.\n"
            "3. Aile-okul-ogrenci uclusunde isbirligi mekanizmasi kurulmasi.\n"
            "4. Ogrenci icin somut, olculebilir kisa vadeli hedefler tanimlanmasi."
        ),
        'uygulanacak_yontemler': (
            "- Haftalik bireysel gorusme (30 dk).\n"
            "- 2 haftada bir veli gorusmesi (telefon veya yuz yuze).\n"
            "- Sinif ogretmenleri ve idare ile aylik koordinasyon toplantisi.\n"
            "- Akademik destek: zayif derslerde etut + ders programi.\n"
            "- Devam takibi: gunluk yoklama bildirimleri.\n"
            "- Davranissal pekistirme: olumlu davranis sozlesmesi.\n"
            "- 4. ve 8. haftada plan etkinligi degerlendirmesi."
        ),
    },
    'genel': {
        'ad': 'Genel Takip Plani',
        'baslik_format': '{ogrenci_ad} - Genel Rehberlik Takip Plani',
        'hedefler': (
            "1. Ogrencinin akademik ve sosyal gelisiminin duzenli takibi.\n"
            "2. Olasi destek ihtiyaclarinin erken tespiti.\n"
            "3. Hedef belirleme ve motivasyon calismasi."
        ),
        'uygulanacak_yontemler': (
            "- Aylik bireysel rehberlik gorusmesi.\n"
            "- Donem sonu performans degerlendirmesi.\n"
            "- Veliyle donem icinde en az iki kez iletisim."
        ),
    },
}


def _sablon_secimi(risk: dict) -> tuple[str, list[str]]:
    """Risk sinyallerine gore en uygun sablon kodu + gerekce listesi."""
    detay = risk.get('detay', {}) or {}
    dev = detay.get('devamsizlik', {}) or {}
    dav = detay.get('davranis', {}) or {}
    den = detay.get('deneme', {}) or {}

    # Sinyal flag'leri
    devamsiz_yuksek = (dev.get('gun_sayisi') or 0) >= 4
    davranis_yuksek = (dav.get('olumsuz_sayi') or 0) >= 2
    akademik_zayif = (
        den.get('trend') == 'dusuyor' or
        (den.get('son_yuzdelik') and den['son_yuzdelik'] >= 80)
    )
    seviye = risk.get('seviye')

    aktif_sinyaller: list[str] = []
    if devamsiz_yuksek:
        aktif_sinyaller.append(f"devamsizlik {dev['gun_sayisi']} gun (30g)")
    if davranis_yuksek:
        aktif_sinyaller.append(f"olumsuz davranis {dav['olumsuz_sayi']} (14g)")
    if akademik_zayif:
        if den.get('trend') == 'dusuyor':
            aktif_sinyaller.append(f"deneme dusus ({den.get('trend_fark', 0):+.1f}p)")
        if den.get('son_yuzdelik') and den['son_yuzdelik'] >= 80:
            aktif_sinyaller.append(f"alt %{100 - den['son_yuzdelik']}'lik dilim")

    # Yuksek seviye + birden fazla aktif alan -> kapsamli
    aktif_alan_sayisi = sum([devamsiz_yuksek, davranis_yuksek, akademik_zayif])
    if seviye == 'yuksek' and aktif_alan_sayisi >= 2:
        return 'kapsamli', aktif_sinyaller

    # Tek baskin alan
    if devamsiz_yuksek and not davranis_yuksek and not akademik_zayif:
        return 'devamsizlik', aktif_sinyaller
    if davranis_yuksek and not devamsiz_yuksek and not akademik_zayif:
        return 'davranis', aktif_sinyaller
    if akademik_zayif and not devamsiz_yuksek and not davranis_yuksek:
        return 'akademik', aktif_sinyaller

    # Birden fazla alan ama yuksek degil -> en agir alan
    if devamsiz_yuksek:
        return 'devamsizlik', aktif_sinyaller
    if davranis_yuksek:
        return 'davranis', aktif_sinyaller
    if akademik_zayif:
        return 'akademik', aktif_sinyaller

    return 'genel', aktif_sinyaller


def plan_sablonu_uret(ogrenci_id: int,
                       sablon_kodu: str | None = None,
                       sure_gun: int = VARSAYILAN_SURE_GUN) -> dict[str, Any]:
    """Bir ogrenci icin risk sinyallerine gore plan sablonu olustur.

    Args:
        ogrenci_id: Ogrenci kimligi.
        sablon_kodu: Belirli bir sablonu zorlamak icin (opsiyonel).
        sure_gun: Plan suresi (varsayilan 56 gun = 8 hafta).
    """
    bugun = date.today()
    ogrenci = Ogrenci.query.get(ogrenci_id)
    if not ogrenci:
        return {'ogrenci': None}

    risk = ogrenci_risk_skoru(ogrenci_id, bugun=bugun)

    if sablon_kodu and sablon_kodu in SABLONLAR:
        secilen = sablon_kodu
        gerekce = ['Manuel sablon secimi']
    else:
        secilen, gerekce = _sablon_secimi(risk)

    sablon = SABLONLAR[secilen]
    baslik = sablon['baslik_format'].format(ogrenci_ad=ogrenci.tam_ad)

    return {
        'ogrenci': ogrenci,
        'risk': risk,
        'sablon_kodu': secilen,
        'sablon_ad': sablon['ad'],
        'baslik': baslik,
        'hedefler': sablon['hedefler'],
        'uygulanacak_yontemler': sablon['uygulanacak_yontemler'],
        'baslangic_tarihi': bugun,
        'bitis_tarihi': bugun + timedelta(days=sure_gun),
        'gerekce': gerekce,
        'tum_sablonlar': [
            {'kod': k, 'ad': v['ad']} for k, v in SABLONLAR.items()
        ],
    }
