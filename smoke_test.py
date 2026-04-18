"""Basit smoke-test: bir rolle login olup tum parametre-siz GET
endpointlerine istek atar ve 500/hata donen URL'leri listeler.

Kullanim:
    python3 smoke_test.py            # admin
    python3 smoke_test.py ogretmen
    python3 smoke_test.py ogrenci
    python3 smoke_test.py veli
"""
from __future__ import annotations

import sys
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.models.user import User


EXCLUDE_ENDPOINTS = {'static', 'auth.cikis'}


def role_login(client, rol):
    with client.application.app_context():
        u = User.query.filter_by(rol=rol, aktif=True).first()
        if not u:
            raise RuntimeError(f'Rol "{rol}" icin aktif kullanici yok')
        uid = u.id
        uname = u.username
    with client.session_transaction() as sess:
        sess['_user_id'] = str(uid)
        sess['_fresh'] = True
    return uid, uname


def main():
    rol = sys.argv[1] if len(sys.argv) > 1 else 'admin'
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    uid, uname = role_login(client, rol)
    print(f'{rol} olarak giris: user_id={uid} ({uname})\n')

    rules = [
        r for r in app.url_map.iter_rules()
        if 'GET' in r.methods and '<' not in r.rule
        and r.endpoint not in EXCLUDE_ENDPOINTS
        and not r.endpoint.startswith('static')
    ]
    rules.sort(key=lambda r: r.rule)
    print(f'{len(rules)} route test edilecek\n')

    sonuc = defaultdict(list)
    for r in rules:
        try:
            resp = client.get(r.rule, follow_redirects=False)
            code = resp.status_code
            snip = ''
            if code >= 500:
                text = resp.get_data(as_text=True)
                for ln in text.split('\n'):
                    ln = ln.strip()
                    if 'Error' in ln or 'Exception' in ln:
                        snip = ln[:200]; break
            sonuc[code].append((r.endpoint, r.rule, snip))
        except Exception as e:
            sonuc['EXC'].append((r.endpoint, r.rule, f'{type(e).__name__}: {e}'))

    print('=' * 70)
    for code in sorted(sonuc, key=str):
        print(f'  HTTP {code}: {len(sonuc[code])} route')

    hatalar = []
    for c in sonuc:
        if c == 'EXC' or (isinstance(c, int) and c >= 500):
            hatalar.extend((c, e, u, s) for e, u, s in sonuc[c])
    if hatalar:
        print('\nHATALAR:')
        for code, ep, url, snip in hatalar:
            print(f'\n[{code}] {url}  ({ep})')
            if snip:
                print(f'     {snip}')
    else:
        print('\nOK - 500/Exception yok.')

    return 1 if hatalar else 0


if __name__ == '__main__':
    sys.exit(main())
