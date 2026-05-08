# 9. Bildirimler ve İletişim

[← İçindekiler](00-index.md) · [← Önceki](08-raporlar.md)

## 9.1. Bildirim çanı

Üst banner'daki **🔔** ikonu sistemdeki tüm uyarıların merkez noktası.

**[Görsel: 09-bildirim-cani-acik.png — Açılır liste]**

Kırmızı sayı = okunmamış bildirim adedi.

## 9.2. Bildirim türleri

| Tür | Kim alır? | Tetikleyici |
|---|---|---|
| Yarın vadesi gelen taksit | Yönetici, Muhasebeci | Otomatik (her gece) |
| Geciken taksit (uyarı) | Yönetici | Vade geçti, hâlâ ödenmedi |
| Eksik not girişi | Öğretmen | Sınav 24h önce, not girilmemiş |
| Yeni veli mesajı | Öğretmen, Yönetici | Veli portaldan mesaj atınca |
| Devamsızlık limiti | Öğretmen, Yönetici | Öğrenci %X devamsızlık geçince |
| Yeni öğrenci kaydı | Yönetici | Kayıt tamamlanınca |
| Sistem duyurusu | Hepsi | Yönetici toplu duyuru attığında |
| Sınav sonuçları açıklandı | Veli, Öğrenci | Deneme puanlama bitince |

## 9.3. Bildirim sayfası

Çanın altındaki **"Tümünü Gör"** linki tüm bildirimleri listeler.

**[Görsel: 09-bildirim-listesi.png — Tablo: bildirim, tarih, okundu/okunmadı]**

Her bildirim:
- Başlık + kısa metin
- Tarih-saat
- **Tıklanabilir** — ilgili sayfaya götürür (örn. taksit detayı)
- "Okundu işaretle" / "Sil" butonları

## 9.4. Toplu Mesaj (SMS)

**Bildirim → Toplu Mesaj**:

**[Görsel: 09-toplu-mesaj.png — Form: hedef, mesaj, önizleme]**

1. **Hedef**: tüm veliler / belirli sınıf / tek öğrenci
2. **Mesaj** (160 karakter sınırı önerilir, daha fazlası 2 SMS sayılır)
3. **Önizleme** (kaç kişi, tahmini maliyet)
4. **Gönder**

> ⚠️ SMS sağlayıcı entegrasyonu için sistem yöneticisi
> [Bölüm 10'daki](10-ayarlar-yetki.md) iletişim ayarlarından
> API anahtarını girmiş olmalı.

## 9.5. E-posta bildirimi

Veliye ya da personele toplu e-posta:

**[Görsel: 09-toplu-eposta.png]**

- Konu + HTML içerik (basit zengin metin editörü)
- Eklenti (PDF) gönderebilirsin
- E-posta adresi tanımlı olanlar listelenir

## 9.6. Ders programı / takvim hatırlatma

Öğrencilere/velilere otomatik:
- Yarın sınav var hatırlatması
- Veli toplantısı duyurusu
- Tatil günü bildirimi

**[Görsel: 09-takvim-hatirlatma.png]**

> Tüm bu otomatik bildirimler, gece çalışan zamanlanmış görev
> tarafından gönderilir; manuel müdahale gerekmez.

## 9.7. Öğretmen mesajlaşması (Veli ↔ Öğretmen)

**İletişim → Mesajlar**:

**[Görsel: 09-mesajlasma.png — Sohbet penceresi]**

- Veli, çocuğunun öğretmenine portal üzerinden mesaj yazar
- Öğretmen sistemde okur ve yanıtlar
- Her mesaj kayıtlı; geçmişe dönük denetlenebilir

---

[← İçindekiler](00-index.md) · [← Önceki](08-raporlar.md) · [Sonraki: Ayarlar ve Yetki →](10-ayarlar-yetki.md)
