"""Parametrik GET route'lari DB'deki ilk mevcut id ile test et."""
from __future__ import annotations

import re
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models.user import User


PARAM_IPUCU = [
    ('ogrenci_id', 'app.models.muhasebe', 'Ogrenci'),
    ('kullanici_id', 'app.models.user', 'User'),
    ('user_id', 'app.models.user', 'User'),
    ('personel_id', 'app.models.muhasebe', 'Personel'),
    ('veli_id', 'app.models.kayit', 'VeliBilgisi'),
    ('kayit_id', 'app.models.kayit', 'OgrenciKayit'),
    ('donem_id', 'app.models.kayit', 'KayitDonemi'),
    ('sube_id', 'app.models.kayit', 'Sube'),
    ('sinif_id', 'app.models.kayit', 'Sinif'),
    ('ders_id', 'app.models.ders_dagitimi', 'Ders'),
    ('sinav_id', 'app.models.not_defteri', 'Sinav'),
    ('duyuru_id', 'app.models.duyurular', 'Duyuru'),
    ('etkinlik_id', 'app.models.duyurular', 'Etkinlik'),
    ('mesaj_id', 'app.models.iletisim', 'Mesaj'),
    ('sablon_id', 'app.models.iletisim', 'MesajSablonu'),
    ('kategori_id', 'app.models.muhasebe', 'GelirGiderKategorisi'),
    ('banka_id', 'app.models.muhasebe', 'BankaHesabi'),
    ('hesap_id', 'app.models.muhasebe', 'BankaHesabi'),
    ('odeme_id', 'app.models.muhasebe', 'OgrenciOdemePlani'),
    ('plan_id', 'app.models.muhasebe', 'OgrenciOdemePlani'),
    ('taksit_id', 'app.models.muhasebe', 'OdemeTaksiti'),
    ('belge_id', 'app.models.kayit', 'OgrenciBelge'),
    ('hatirlatma_id', 'app.models.duyurular', 'Hatirlatma'),
    ('gorusme_id', 'app.models.rehberlik', 'Gorusme'),
    ('profil_id', 'app.models.rehberlik', 'OgrenciProfili'),
    ('plan_id', 'app.models.rehberlik', 'RehberlikPlani'),
    ('kayit_id', 'app.models.davranis', 'DavranisKaydi'),
    ('kural_id', 'app.models.davranis', 'DavranisKurali'),
    ('kulup_id', 'app.models.kulupler', 'Kulup'),
    ('anket_id', 'app.models.online_sinav', 'OnlineSinav'),
    ('karne_id', 'app.models.karne', 'Karne'),
    ('ders_notu_id', 'app.models.karne', 'KarneDersNotu'),
    ('odev_id', 'app.models.not_defteri', 'OdevTakip'),
    ('etut_id', 'app.models.etut', 'Etut'),
    ('guzergah_id', 'app.models.servis', 'Guzergah'),
    ('durak_id', 'app.models.servis', 'ServisDurak'),
    ('arac_id', 'app.models.servis', 'Arac'),
    ('demirbas_id', 'app.models.envanter', 'Demirbas'),
    ('oda_id', 'app.models.yurt', 'YurtOda'),
    ('soru_id', 'app.models.online_sinav', 'SinavSoru'),
    ('soru_id', 'app.models.anket', 'AnketSoru'),
    ('kitap_id', 'app.models.kutuphane', 'Kitap'),
    ('kisi_id', 'app.models.iletisim', 'IletisimDefteri'),
    ('katilim_id', 'app.models.online_sinav', 'SinavKatilim'),
    ('menu_id', 'app.models.kantin', 'YemekMenu'),
    ('urun_id', 'app.models.kantin', 'KantinUrun'),
]

# Endpoint-spesifik 'id' parametresi cozumleri (ambiguous 'id' icin)
ENDPOINT_ID = {
    'kurum.derslik.duzenle': ('app.models.kurum', 'Derslik'),
    'kurum.ogretim_yili.duzenle': ('app.models.kurum', 'OgretimYili'),
    'kurum.tatil.duzenle': ('app.models.kurum', 'Tatil'),
    'muhasebe.gelir_gider.duzenle': ('app.models.muhasebe', 'GelirGiderKaydi'),
}


EXCLUDE = {'static', 'auth.cikis'}


def ilk_id(app, param):
    with app.app_context():
        for pname, mod_path, cls_name in PARAM_IPUCU:
            if param != pname:
                continue
            try:
                mod = __import__(mod_path, fromlist=[cls_name])
                cls = getattr(mod, cls_name)
                row = cls.query.first()
                if row:
                    return row.id
            except Exception:
                continue
    return None


def admin_login(client):
    with client.application.app_context():
        admin = User.query.filter_by(rol='admin').first()
        uid = admin.id
    with client.session_transaction() as sess:
        sess['_user_id'] = str(uid)
        sess['_fresh'] = True


def ilk_id_endpoint(app, endpoint):
    """Endpoint-spesifik 'id' icin model lookup."""
    if endpoint not in ENDPOINT_ID:
        return None
    mod_path, cls_name = ENDPOINT_ID[endpoint]
    with app.app_context():
        try:
            mod = __import__(mod_path, fromlist=[cls_name])
            cls = getattr(mod, cls_name)
            row = cls.query.first()
            return row.id if row else None
        except Exception:
            return None


def build_url(rule_str, app, endpoint=None):
    pat = re.compile(r'<(?:\w+:)?(\w+)>')
    params = pat.findall(rule_str)
    values = {}
    for p in params:
        v = None
        if p == 'id' and endpoint:
            v = ilk_id_endpoint(app, endpoint)
        if v is None:
            v = ilk_id(app, p)
        if v is None:
            if 'kod' in p or 'slug' in p:
                v = 'test'
            elif 'tarih' in p:
                v = '2026-01-01'
            elif 'turu' in p or 'tur' in p:
                v = 'excel'
            elif p.endswith('_id') or p == 'id':
                # Tablo bos olabilir; yine de 1 ile dene (get_or_404 yolunu test et)
                v = 1
            else:
                return None
        values[p] = v
    url = rule_str
    for k, v in values.items():
        url = re.sub(rf'<(?:[^:>]+:)?{k}>', str(v), url)
    return url


def main():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    admin_login(client)

    rules = [
        r for r in app.url_map.iter_rules()
        if 'GET' in r.methods and '<' in r.rule
        and r.endpoint not in EXCLUDE
        and not r.endpoint.startswith('static')
    ]
    print(f'{len(rules)} parametrik GET route\n')

    sonuc = defaultdict(list)
    atlandi = []
    for r in rules:
        url = build_url(r.rule, app, r.endpoint)
        if url is None:
            atlandi.append((r.endpoint, r.rule))
            continue
        try:
            resp = client.get(url, follow_redirects=False)
            code = resp.status_code
            snip = ''
            if code >= 500:
                text = resp.get_data(as_text=True)
                for ln in text.split('\n'):
                    ln = ln.strip()
                    if 'Error' in ln or 'Exception' in ln:
                        snip = ln[:220]; break
            sonuc[code].append((r.endpoint, r.rule, url, snip))
        except Exception as e:
            sonuc['EXC'].append((r.endpoint, r.rule, url, f'{type(e).__name__}: {e}'))

    print('=' * 70)
    for code in sorted(sonuc, key=str):
        print(f'  HTTP {code}: {len(sonuc[code])}')
    print(f'  ATLANDI: {len(atlandi)}')

    hatalar = []
    for c in sonuc:
        if c == 'EXC' or (isinstance(c, int) and c >= 500):
            hatalar.extend((c, e, rule, url, s) for e, rule, url, s in sonuc[c])
    if hatalar:
        print(f'\nHATALAR ({len(hatalar)}):')
        for code, ep, rule, url, snip in hatalar:
            print(f'\n[{code}] {url}  ({ep})')
            if snip:
                print(f'     {snip}')
    else:
        print('\nOK - 500/Exception yok.')

    return 1 if hatalar else 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
