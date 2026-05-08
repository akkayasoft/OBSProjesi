# 11. Veritabanı Yedekleme ve Geri Yükleme

[← İçindekiler](00-index.md) · [← Önceki](10-ayarlar-yetki.md)

> ⚠️ Sadece **Sistem Yöneticisi** ve **Yönetici** erişebilir.
> Yedek alma güvenli; **geri yükleme destruktiftir**.

## 11.1. Yedekleme sayfasına erişim

Sol menü → **Sistem Ayarları → Veritabanı Yedekleme**.

Sürücü kursunda: **Ayarlar → Veritabanı Yedekleme**.

**[Görsel: 11-yedekleme-anasayfa.png — Sayfa: yedek al kartı + geri yükle kartı]**

Sayfada iki kart var:
- **Sol**: Yedek İndir
- **Sağ**: Yedeği Geri Yükle (kırmızı çerçeve)

## 11.2. Yedek alma

### Adımlar

1. **"Yedek İndir"** butonuna bas
2. Sistem `pg_dump` ile DB'nizi alır → **gzip** ile sıkıştırır
3. Tarayıcıya `.sql.gz` dosyası iner

**[Görsel: 11-yedek-indir.png — İndirme penceresi: dosya adı, boyut]**

Dosya adı şu formatta:
```
<dershane_db_adi>_YYYYMMDD_HHMMSS.sql.gz
```

Örnek: `obs_bilfen_20260508_143025.sql.gz`

### Önerilen sıklık
- **Günlük**: kritik dönemlerde (kayıt sezonu, sınav haftası)
- **Haftalık**: düzenli rutin
- **Önemli işlem öncesi**: toplu silme/değişiklik öncesi

> 💡 Bilgisayarınızda **yedekler** klasörü açıp yedekleri tarihli
> şekilde saklayın. Sunucu çökerse bu yedek kurtarıcınızdır.

## 11.3. Yedeği geri yükleme

> 🚨 **DİKKAT**: Bu işlem **mevcut tüm verilerinizi siler** ve seçtiğiniz
> yedekteki haline döner. **Geri alınamaz.**

### Ön hazırlık

1. **Mevcut durumu bir kez daha yedekle** (her ihtimale karşı)
2. **Başka kimse sistemde çalışmazken** yap (gece tercihi)
3. **Hangi yedeği yükleyeceksiniz** kontrol edin (tarih, dershane adı)

### Adımlar

**[Görsel: 11-geri-yukle-formu.png — Geri yükleme formu]**

1. **"Yedeği Geri Yükle"** kartında:
   - **Yedek dosyası** seç (`.sql.gz` veya `.sql`)
   - **Onay metni** alanına büyük harfle **`GERI YUKLE`** yaz
   - **"Yedeği Geri Yükle"** butonuna bas
2. Tarayıcı bir kez daha onay sorar: **"Devam edilsin mi?"** → Tamam
3. İşlem 30 sn — 2 dk arası sürer (DB boyutuna göre)
4. Tamamlanınca otomatik **çıkışa zorlanırsınız** → tekrar giriş yapın

**[Görsel: 11-geri-yukle-tamam.png — Login sayfasında "Yedek başarıyla yüklendi" mesajı]**

### Sistem otomatik olarak ne yapar?

1. **Onay metni doğrulanır** (`GERI YUKLE` değilse durur)
2. Yüklenen dosyanın PostgreSQL dump olduğu kontrol edilir
3. **"Öncesi" yedek otomatik alınır** (`/var/backups/obs_restore/` veya
   `/tmp/`) — hata durumunda elle geri dönüş için
4. Veritabanına aktif tüm bağlantılar **terminate** edilir
5. DB **DROP + CREATE** edilir
6. `psql -f` ile yeni yedek **uygulanır** (10 dk timeout)
7. Sistem session'ları temizlenir, login sayfasına yönlendirilirsiniz

## 11.4. Hata durumunda

### "Onay metni hatalı"
`GERI YUKLE` (boşluksuz, büyük harf, T'siz) yazmamış olabilirsiniz.

### "Yedek dosyası çok büyük"
Üst sınır 200 MB. Çok büyük yedekler için sistem yöneticisine başvurun
(elle psql ile yüklenebilir).

### "psql restore hata"
Genellikle yedek dosyası bozuk veya farklı versiyon Postgres'ten.
Flash mesajda **öncesi yedek dosyasının yolu** verilir; sistem
yöneticiniz oradan elle geri yükleyebilir:

```bash
# Sunucuda root olarak
gunzip -c /var/backups/obs_restore/oncesi_obs_bilfen_20260508.sql.gz \
  | psql -d obs_bilfen
```

## 11.5. Otomatik gece yedeği (sunucu)

Sunucuda her gece **02:00'de otomatik yedek** çalışır (cron job).
Yedekler `/var/backups/obs/` altında 7 gün saklanır.

> Bu yedeklere erişim sistem yöneticisi (root) düzeyinde olduğu için,
> tenant yöneticisi UI'dan görmez. Felaket senaryosunda sistem
> yöneticinizle iletişime geçin.

## 11.6. Test ortamında deneme

İlk kez geri yükleme yapacaksanız:
1. **Test tenant'ı oluşturun** (sistem panelinden)
2. Mevcut yedeği oraya yükleyin
3. Veriler doğru göründüyse asıl tenant'a uygulayın

> Bu sayede gerçek veriyi kaybetme riski olmadan akışı test edersiniz.

---

[← İçindekiler](00-index.md) · [← Önceki](10-ayarlar-yetki.md)

## Tebrikler! 🎉

Tüm kullanım kılavuzunu tamamladınız. Sorularınız için sistem
yöneticinizle veya destek ekibiyle iletişime geçin.
