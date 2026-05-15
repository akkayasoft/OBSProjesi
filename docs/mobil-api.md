# OBS Mobil API — v1 Dokümantasyonu

Bu doküman, OBS öğrenci/veli mobil uygulamasının kullandığı JSON API'sini
tanımlar. API web portalından bağımsızdır; `/api/v1` öneki altında çalışır.

> **Sözleşme:** Bu API yüzeyi sabittir. Mobil uygulama (Flutter) yalnızca
> bu dokümana göre yazılır; OBS backend kodunu bilmesi gerekmez.

---

## 1. Genel Bilgiler

### Temel URL

Her dershane kendi alt alan adında (subdomain) çalışır:

```
https://<kurum-kodu>.obs.akkayasoft.com/api/v1
```

Örnek: `bilfen` kurum kodu için
`https://bilfen.obs.akkayasoft.com/api/v1`

> **Çoklu-kiracı (multi-tenant):** Mobil uygulama açılışta kullanıcıdan
> **kurum kodu** ister, bu kodla temel URL'yi oluşturur ve tüm istekleri
> o adrese yapar. Bir kurumun token'ı başka kurumda geçersizdir.

### Kimlik doğrulama

- Token tabanlı (JWT). Web'deki çerez/oturum kullanılmaz.
- `POST /auth/login` ile token alınır.
- Sonraki tüm isteklerde HTTP başlığı:
  ```
  Authorization: Bearer <token>
  ```
- Token **30 gün** geçerlidir. Süre dolunca tekrar login gerekir.

### Standart yanıt biçimi

**Başarılı:**
```json
{
  "basarili": true,
  "veri": { ... }
}
```
Bazı uç noktalar `veri` yanında ek alanlar döner (`okunmamis`,
`ogrenci`, `ozet` gibi).

**Hata:**
```json
{
  "basarili": false,
  "hata": "Açıklayıcı hata mesajı"
}
```

### HTTP durum kodları

| Kod | Anlamı |
|-----|--------|
| 200 | Başarılı |
| 400 | Eksik/geçersiz istek |
| 401 | Token yok / geçersiz / süresi dolmuş |
| 403 | Yetki yok (ör. pasif hesap) |
| 404 | Kaynak bulunamadı |
| 405 | Yanlış HTTP metodu |
| 500 | Sunucu hatası |

---

## 2. Kimlik Doğrulama

### POST /auth/login

Kullanıcı adı + şifre ile token alır. Token gerektirmez.

**İstek gövdesi (JSON):**
```json
{
  "kullanici_adi": "ogrenci123",
  "sifre": "sifre123"
}
```
> `kullanici_adi` yerine `username`, `sifre` yerine `password` da
> kabul edilir. Kullanıcı adı yerine e-posta da girilebilir.

**Başarılı yanıt (200):**
```json
{
  "basarili": true,
  "veri": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "gecerlilik_gun": 30,
    "kullanici": {
      "id": 42,
      "ad": "Ali",
      "soyad": "Yılmaz",
      "tam_ad": "Ali Yılmaz",
      "rol": "ogrenci",
      "rol_adi": "Öğrenci",
      "email": "ali@ornek.com"
    }
  }
}
```

**Hata yanıtları:**
- `400` — kullanıcı adı veya şifre eksik
- `401` — kullanıcı adı veya şifre hatalı
- `403` — hesap pasif

**Örnek (curl):**
```bash
curl -X POST https://bilfen.obs.akkayasoft.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"kullanici_adi":"ogrenci123","sifre":"sifre123"}'
```

### GET /me

Geçerli token'ın sahibi kullanıcının bilgisi. Token testi için kullanılır.

**Başarılı yanıt (200):**
```json
{
  "basarili": true,
  "veri": {
    "kullanici": {
      "id": 42, "ad": "Ali", "soyad": "Yılmaz",
      "tam_ad": "Ali Yılmaz", "rol": "ogrenci",
      "rol_adi": "Öğrenci", "email": "ali@ornek.com"
    }
  }
}
```

---

## 3. Bildirimler

### GET /bildirimler

Kullanıcının bildirimleri (en yeni önce, son 50 kayıt).

**Başarılı yanıt (200):**
```json
{
  "basarili": true,
  "okunmamis": 3,
  "veri": [
    {
      "id": 101,
      "baslik": "Devamsızlık Bildirimi",
      "mesaj": "4 Mayıs günü 2 ders saati devamsız.",
      "tur": "uyari",
      "kategori": "devamsizlik",
      "link": "/portal/devamsizlik/",
      "okundu": false,
      "tarih": "2026-05-04T10:30:00"
    }
  ]
}
```

`tur`: `bilgi` / `uyari` / `basari` / `hata`
`kategori`: `mesaj` / `not` / `devamsizlik` / `duyuru` / `sinav` /
`odeme` / `sistem` / `diger`

### POST /bildirimler/{id}/okundu

Tek bir bildirimi okundu işaretler.

**Başarılı yanıt (200):**
```json
{ "basarili": true, "veri": { "id": 101, "okundu": true } }
```
**Hata:** `404` — bildirim bulunamadı (veya başka kullanıcıya ait)

### POST /bildirimler/tumunu-okundu

Tüm okunmamış bildirimleri okundu işaretler.

**Başarılı yanıt (200):**
```json
{ "basarili": true, "veri": { "okundu_isaretlenen": 3 } }
```

---

## 4. Duyurular

### GET /duyurular

Kullanıcının rolüne uygun aktif duyurular (sabitlenmişler önce).

**Başarılı yanıt (200):**
```json
{
  "basarili": true,
  "veri": [
    {
      "id": 7,
      "baslik": "Yarıyıl Tatili",
      "icerik": "Okul 20 Ocak'ta tatile girecektir.",
      "kategori": "genel",
      "oncelik": "normal",
      "sabitlenmis": true,
      "okundu": false,
      "tarih": "2026-01-10T09:00:00"
    }
  ]
}
```

### GET /duyurular/{id}

Tek duyuru detayı. Görüntülendiğinde otomatik okundu kaydı oluşur.

**Başarılı yanıt (200):** tek duyuru nesnesi (`okundu: true`)
**Hata:** `404` — duyuru bulunamadı veya pasif

---

## 5. Devamsızlık

### GET /devamsizlik

Öğrencinin devamsızlık kayıtları ve özeti.
**Öğrenci** kendi kayıtlarını, **veli** bağlı olduğu öğrencinin
kayıtlarını görür.

**Sorgu parametresi (opsiyonel):**
- `ay` — `YYYY-MM` biçiminde aya göre filtre. Örn: `?ay=2026-05`

**Başarılı yanıt (200):**
```json
{
  "basarili": true,
  "ogrenci": {
    "id": 12, "ad_soyad": "Ali Yılmaz",
    "ogrenci_no": "1234", "sinif": "9. Sınıf - A"
  },
  "ozet": {
    "devamsiz": 2, "gec": 1, "izinli": 0,
    "raporlu": 0, "toplam": 3
  },
  "veri": [
    {
      "id": 55, "tarih": "2026-05-04",
      "ders_saati": 2, "durum": "devamsiz",
      "aciklama": null
    }
  ]
}
```
`durum`: `devamsiz` / `gec` / `izinli` / `raporlu`

**Hata:** `404` — hesaba bağlı öğrenci bulunamadı

---

## 6. Ödeme / Borç Durumu

### GET /odemeler

Öğrencinin ödeme planları, taksitleri ve borç özeti.

**Başarılı yanıt (200):**
```json
{
  "basarili": true,
  "ogrenci": {
    "id": 12, "ad_soyad": "Ali Yılmaz",
    "ogrenci_no": "1234", "sinif": "9. Sınıf - A"
  },
  "veri": {
    "ozet": {
      "toplam_borc": 9000.0,
      "odenen": 3000.0,
      "kalan": 6000.0,
      "geciken_taksit": 1
    },
    "planlar": [
      {
        "id": 3, "donem": "2025-2026",
        "net_tutar": 9000.0, "odenen": 3000.0,
        "kalan": 6000.0, "taksit_sayisi": 3, "durum": "aktif",
        "taksitler": [
          {
            "taksit_no": 1, "tutar": 3000.0, "odenen": 3000.0,
            "kalan": 0.0, "vade_tarihi": "2026-05-01",
            "odeme_tarihi": "2026-05-01", "durum": "odendi",
            "gecikti_mi": false
          }
        ]
      }
    ]
  }
}
```
Taksit `durum`: `beklemede` / `odendi` / `gecikti` /
`kismi_odendi` / `ertelendi`

**Hata:** `404` — hesaba bağlı öğrenci bulunamadı

---

## 7. Deneme Sınavları

### GET /denemeler

Öğrencinin katıldığı deneme sınavları (en yeni önce).

**Başarılı yanıt (200):**
```json
{
  "basarili": true,
  "ogrenci": { "id": 12, "ad_soyad": "Ali Yılmaz", "...": "..." },
  "veri": [
    {
      "katilim_id": 88,
      "sinav": {
        "id": 5, "ad": "TYT Deneme 1",
        "tip": "TYT", "tarih": "2026-05-01"
      },
      "toplam_dogru": 35, "toplam_yanlis": 20,
      "toplam_bos": 25, "toplam_net": 30.0,
      "toplam_puan": 300.0
    }
  ]
}
```

### GET /denemeler/{katilim_id}

Bir deneme katılımının ders bazlı detayı + sıralama.

**Başarılı yanıt (200):**
```json
{
  "basarili": true,
  "ogrenci": { "id": 12, "ad_soyad": "Ali Yılmaz", "...": "..." },
  "veri": {
    "katilim_id": 88,
    "sinav": {
      "id": 5, "ad": "TYT Deneme 1", "tip": "TYT",
      "tarih": "2026-05-01", "ortalama_net": 25.5
    },
    "sonuc": {
      "toplam_dogru": 35, "toplam_yanlis": 20,
      "toplam_bos": 25, "toplam_net": 30.0, "toplam_puan": 300.0
    },
    "siralama": 2,
    "toplam_katilimci": 40,
    "ders_sonuclari": [
      { "ders": "Türkçe", "dogru": 20, "yanlis": 8,
        "bos": 12, "net": 18.0 }
    ]
  }
}
```
**Hata:** `404` — katılım bulunamadı veya başka öğrenciye ait

---

## 8. Uygulama İçin Notlar

### Önerilen akış

1. **Açılış:** Kurum kodu sorulur → temel URL oluşturulur.
2. **Giriş:** `POST /auth/login` → token cihazda güvenli depolanır
   (Flutter: `flutter_secure_storage`).
3. **Sonraki istekler:** Her isteğe `Authorization: Bearer <token>`.
4. **401 yanıtı:** Token süresi dolmuş → kullanıcı login ekranına
   yönlendirilir.

### Roller

API'ye her rol giriş yapabilir; ancak v1 uç noktaları
**öğrenci ve veli** odaklıdır:
- `ogrenci` — kendi verisini görür
- `veli` — bağlı olduğu öğrencinin verisini görür
- Diğer roller `devamsizlik`/`odemeler`/`denemeler` çağırırsa
  `404` (bağlı öğrenci yok) alır.

### Güvenlik

- Tüm veri sorguları kullanıcıyla sınırlıdır; bir kullanıcı
  başkasının bildirimine/sonucuna erişemez.
- Token yalnızca alındığı kuruma (subdomain) geçerlidir.

---

## 9. Endpoint Özeti

| Metot | Yol | Token | Açıklama |
|-------|-----|:-----:|----------|
| POST | `/auth/login` | — | Token al |
| GET  | `/me` | ✓ | Kullanıcı bilgisi |
| GET  | `/bildirimler` | ✓ | Bildirim listesi |
| POST | `/bildirimler/{id}/okundu` | ✓ | Bildirimi okundu yap |
| POST | `/bildirimler/tumunu-okundu` | ✓ | Hepsini okundu yap |
| GET  | `/duyurular` | ✓ | Duyuru listesi |
| GET  | `/duyurular/{id}` | ✓ | Duyuru detayı |
| GET  | `/devamsizlik` | ✓ | Devamsızlık + özet |
| GET  | `/odemeler` | ✓ | Ödeme planları + borç |
| GET  | `/denemeler` | ✓ | Deneme sınavı listesi |
| GET  | `/denemeler/{id}` | ✓ | Deneme detayı + sıralama |

---

*Sürüm: v1 · Son güncelleme: 2026-05*
