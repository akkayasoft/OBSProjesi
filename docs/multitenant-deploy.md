# Multi-tenant (SaaS) Deploy Rehberi

Bu dokuman `MULTITENANT_ENABLED=1` bayragini VPS'te guvenli sekilde acmak
icin adim adim talimatlari icerir. Mevcut `obs.akkayasoft.com` kurulumu
(tek veritabani) hic kesintiye ugramadan "default" tenant olarak korunur,
sonra `*.obs.akkayasoft.com` uzerinden yeni kurumlar eklenir.

> **Ozet akis:** master DB kur -> .env guncelle -> mevcut DB'yi default
> tenant olarak kaydet -> wildcard DNS + SSL -> Nginx wildcard -> flag on.

## 0. Ongerekler

- VPS: `root@187.127.68.167`, Postgres + Nginx + systemd (`obs.service`) hazir.
- Domain: `obs.akkayasoft.com` (A record mevcut, Let's Encrypt SNI calisir).
- Kod: `c4b4b00` ve sonrasi VPS'e pull edilmis (`git log -1`).

## 1. Master veritabanini olustur

Master DB sadece `tenants` tablosunu tutar; kurum verileriyle karismaz.

```bash
sudo -u postgres psql <<'SQL'
CREATE DATABASE obs_master OWNER obs;
GRANT ALL PRIVILEGES ON DATABASE obs_master TO obs;
SQL
```

Eger `obs_master` kullanicisi/sifresi farkliysa mevcut ayarlarina uyarla.
`CREATE DATABASE` yetkili ikinci bir kullanici (`obs_admin`) tenant olustururken
`--create-db` icin gerekir:

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE obs_admin WITH LOGIN CREATEDB PASSWORD 'GUCLU_SIFRE';
SQL
```

## 2. .env dosyasini guncelle

`/var/www/obs/.env` uzerine sunlari EKLE (mevcut satirlara dokunma):

```dotenv
# --- Multi-tenant ---
MULTITENANT_ENABLED=0
TENANT_ROOT_DOMAIN=obs.akkayasoft.com
TENANT_DEFAULT_SLUG=default

MASTER_DATABASE_URL=postgresql://obs:OBS_SIFRESI@localhost/obs_master
TENANT_DATABASE_URL_TEMPLATE=postgresql://obs:OBS_SIFRESI@localhost/{db_name}
TENANT_ADMIN_DATABASE_URL=postgresql://obs_admin:GUCLU_SIFRE@localhost/postgres
```

> `MULTITENANT_ENABLED=0` tutuyoruz — bu asamada sadece master DB + CLI
> hazirlanacak, istek yonlendirmesi hala klasik mod. Servisi yeniden
> baslatmaya simdi gerek yok.

## 3. Master tabloyu olustur ve mevcut DB'yi default tenant olarak kaydet

Mevcut uretim DB'si ornegin `obs` adinda. Onu silmeden "default" tenant
olarak isaretleyecegiz — `*.obs.akkayasoft.com` kapsamadigi icin
`obs.akkayasoft.com` (root) ziyaretleri TENANT_DEFAULT_SLUG sayesinde bu
tenant'a duser. Mevcut kullanicilar hicbir sey fark etmez.

```bash
cd /var/www/obs
source venv/bin/activate
export FLASK_APP=wsgi.py

flask tenant init-master
flask tenant create default --ad "OBS Default" --db-name obs
flask tenant list
```

`--create-db` BAYRAGINI KULLANMA — mevcut DB'yi silmemeliyiz, sadece
master tabloya referans ekliyoruz.

## 4. Wildcard DNS kaydi (Hostinger panel)

Hostinger -> Domains -> `akkayasoft.com` -> DNS / Nameservers:

| Type | Name              | Points to         | TTL  |
|------|-------------------|-------------------|------|
| A    | `*.obs`           | `187.127.68.167`  | 3600 |

(Root `obs.akkayasoft.com` A kaydi zaten var.) Propagasyon icin 5–30 dk.
Test:

```bash
dig +short foo.obs.akkayasoft.com   # -> 187.127.68.167 donmeli
```

## 5. Wildcard SSL (Let's Encrypt DNS-01)

HTTP-01 wildcard yapmaz — DNS-01 sart. Hostinger Certbot DNS plugin'i
olmadigindan **manual mode** kullaniyoruz (yilda 2 kez yenilenir ama
her seferinde DNS TXT eklemek gerekir; istenirse acme-dns/lego ile
otomatiklestirilebilir, simdilik basit yontem):

```bash
certbot certonly --manual --preferred-challenges=dns \
  -d obs.akkayasoft.com -d '*.obs.akkayasoft.com' \
  --agree-tos -m ayhanakkayameb@gmail.com
```

Certbot `_acme-challenge.obs.akkayasoft.com` icin TXT kaydi isteyecek.
Hostinger DNS panelinden ekle, TTL 60, 1-2 dk propagasyonu bekle,
`dig +short TXT _acme-challenge.obs.akkayasoft.com` ile dogrula, sonra
Enter. Sertifika `/etc/letsencrypt/live/obs.akkayasoft.com/` altina duser.

> **Otomatik yenileme alternatifi:** `lego` + Hostinger API plugin'i
> ya da `acme-dns` rolet — opsiyonel 2. faz.

## 6. Nginx wildcard server_name

`/etc/nginx/sites-available/obs` dosyasini duzenle — TEK degisiklik
`server_name` satirini wildcard'li hale getirmek:

```nginx
server {
    server_name obs.akkayasoft.com *.obs.akkayasoft.com;   # <-- wildcard eklendi
    client_max_body_size 20M;

    location /static/ {
        alias /var/www/obs/app/static/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;                  # <-- middleware bunu okuyor
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    listen [::]:443 ssl ipv6only=on;
    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/obs.akkayasoft.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/obs.akkayasoft.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if ($host ~* ^(.+\.)?obs\.akkayasoft\.com$) {   # <-- wildcard redirect
        return 301 https://$host$request_uri;
    }
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name obs.akkayasoft.com *.obs.akkayasoft.com;
    return 404;
}
```

```bash
nginx -t && systemctl reload nginx
```

## 7. Flag'i acmak (geri donulebilir)

```bash
# /var/www/obs/.env icinde
MULTITENANT_ENABLED=1
```

```bash
systemctl restart obs
systemctl status obs
curl -sI https://obs.akkayasoft.com/auth/giris | head -1   # 200/302 — default tenant
```

Sorun cikarsa bayragi kapat + restart — uygulama 5 sn icinde eski
davranisina doner.

## 8. Yeni bir kurum eklemek

```bash
cd /var/www/obs && source venv/bin/activate
export FLASK_APP=wsgi.py

flask tenant create cadde \
  --ad "Cadde Dershanesi" \
  --db-name obs_cadde \
  --create-db \
  --email info@caddedershanesi.com
```

Komut sirasiyla:
1. `obs_admin` ile `CREATE DATABASE obs_cadde` yapar,
2. `DATABASE_URL=postgresql://.../obs_cadde` override'i ile `flask db upgrade` calistirir,
3. Master tabloda kayit olusturur (durum=aktif).

Sonra `https://cadde.obs.akkayasoft.com/` acilabilir. Ilk admin
olusturmak icin (istege bagli):

```bash
DATABASE_URL=postgresql://obs:SIFRE@localhost/obs_cadde \
MULTITENANT_ENABLED=0 \
FLASK_APP=wsgi.py \
flask seed   # mevcut seed komutu varsa
```

## 9. Abonelik / askiya alma

```bash
flask tenant set-status cadde askida     # 503 doner
flask tenant set-status cadde aktif      # tekrar erisime acar
```

Abonelik bitisi otomatik: `abonelik_bitis` gecmisse `aktif_mi` False
doner, istek 503 yer. UI tabanli yonetim panel'i 2. faz.

## 10. Toplu migrate (yeni versiyon deploy'unda)

```bash
cd /var/www/obs && git pull
source venv/bin/activate
pip install -q -r requirements.txt

# Default + tum aktif tenantlarda migration:
flask tenant migrate-all

systemctl restart obs
```

`migrate-all` her aktif tenant icin subprocess ile `flask db upgrade`
calistirir (DATABASE_URL override ederek), bu sayede tek komutla tum
kurumlar guncel semaya gecer.

## Riskler ve notlar

- **Connection pool**: Her tenant 5 connection ayirir. 10 kurum = 50 conn.
  Postgres `max_connections` (varsayilan 100) yeterli ama cok tenant
  eklenirse `TENANT_DB_POOL_SIZE` dusurulebilir.
- **Engine cache**: 50 tenant'a kadar bellekte tutulur, sonrasi LRU ile
  dispose edilir; istendigi an tekrar acilir.
- **Session**: `db.session` middleware sayesinde otomatik dogru tenant'a
  baglanir — mevcut kod (400+ view) hic degismedi.
- **Master backup**: `pg_dump obs_master` kucuk ve kritik, gunluk backup'a
  ekle. Tenant DB'leri ayri ayri backup'lanmali (bir tenant kaybi digerini
  etkilemez, bu guzel izolasyon ama backup stratejisini ozenle yap).
- **Admin paneli**: Simdilik CLI uzerinden yonetiyoruz. Master admin
  paneli (tenant CRUD, fatura, durum gorsel) 2. faz.
