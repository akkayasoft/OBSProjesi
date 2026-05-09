# 8. Raporlar ve Bekleyen Tahsilat

[← İçindekiler](00-index.md) · [← Önceki](07-muhasebe.md)

## 8.1. Raporlar ana sayfası

Sol menü → **Raporlama** (veya bazı kurum tiplerinde **Raporlar**).

![KPI kartları + grafik bölümleri](gorseller/08-rapor-anasayfa.svg)

KPI kartları:
- Aktif öğrenci / personel
- Bu ay net (gelir − gider)
- **Bekleyen Tahsilat** (sarı, **tıklanabilir** — detaylı sayfa açılır)
- Geciken taksit sayısı

## 8.2. Bekleyen Tahsilat detayı

KPI kartına tıklayınca → **`/rapor/bekleyen-tahsilat`** sayfası.

![Tablo: kim ne kadar borçlu, geciken kırmızı](gorseller/08-bekleyen-tahsilat.svg)

### Üst kartlar
- Borçlu öğrenci sayısı
- Toplam bekleyen
- Geciken tutar
- Geciken taksit adedi

### Tablo
| Kolon | Anlamı |
|---|---|
| Öğrenci | Ad-soyad + TC |
| Telefon | İletişim |
| Sınıf / Dönem | Bağlı olduğu grup |
| Borçlu Taksit | Adet |
| Geciken | Adet (kırmızı badge) |
| En Yakın Vade | Geçmişse uyarı |
| Bekleyen Tutar | Toplam ₺ |

Geciken kursiyerlerin satırı kırmızı (`table-danger`) ile vurgulanır.

### Filtreler
- Dönem (ay bazlı)
- Sınıf / ehliyet sınıfı
- Sıralama: kalan tutar ↓ / vade ↑ / ad

## 8.3. Mali grafikler

Rapor sayfasının altında trend grafikleri:

![6 ay gelir/gider/net çizgi grafiği](gorseller/08-mali-trend.svg)

- **Mali trend** (son 6 ay): gelir/gider/net çizgisi
- **Aylık tahsilat trendi**: kursiyer ödemelerinin ay başına toplamı
- **Ödeme türü dağılımı** (son 90 gün): nakit/EFT/kredi kartı yüzdeleri

## 8.4. Sınıf / Dönem bazlı raporlar

![Sınıf adı, öğrenci sayısı, toplam ücret, tahsilat](gorseller/08-sinif-bazli.svg)

- Sınıf bazlı doluluk
- Sınıf bazlı tahsilat oranı
- Dönem bazlı kayıt eğrisi

## 8.5. Eğitmen / Öğretmen performansı

**Raporlar → Eğitmen Performansı**:

![08-egitmen-rapor](gorseller/08-egitmen-rapor.svg)

- Öğretmen başına aktif öğrenci sayısı
- Toplam ciro
- Sınav sonuç ortalamaları

## 8.6. Yıl bazı sınav harç toplamı

![08-sinav-harc-yillik](gorseller/08-sinav-harc-yillik.svg)

- Tahsil edilen toplam (yeşil)
- Bekleyen toplam (sarı)
- Aday borçlu sayısı

## 8.7. Komisyon Özeti (Sürücü Kursu)

Sürücü kursu tenant'larında ek bölüm:

![2 yan yana kart](gorseller/08-komisyon-ozeti.svg)

- **Yönlendirme Komisyonu** (gelir): toplam / tahsil edilen / bekleyen
- **Komisyon Ödemeleri** (gider): toplam / ödenen / bekleyen

## 8.8. Dışa aktarım

Hemen her rapor sayfasında **"Excel'e Aktar"** veya **"PDF Olarak İndir"**
butonu mevcuttur. Yönetim toplantısına götürmek için kullanışlı.

![Excel/PDF butonları](gorseller/08-disa-aktar.svg)

> 💡 **Tarayıcı yazdırma** ile her rapor sayfası A4 PDF'e dökülebilir.
> Sayfa altındaki gereksiz öğeler @media print CSS ile gizlenir.

---

[← İçindekiler](00-index.md) · [← Önceki](07-muhasebe.md) · [Sonraki: Bildirimler →](09-bildirim.md)
