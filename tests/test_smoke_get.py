"""GET endpoint smoke testi — paylasilan kod koruma agi.

Tum parametre-siz GET sayfalari, admin oturumuyla 500 / Exception
vermemeli. base.html, app/__init__.py, _layout.html gibi paylasilan
dosyalara dokunuldugunda bir sayfanin bozuldugunu otomatik yakalar.

Bu test 'X ozelligi eklerken Y sayfasini bozdum' regresyonunu
deploy oncesi (deploy.sh [4/8]) durdurur.
"""

# Bilincli haric tutulanlar — cikis (session bozar), statik dosyalar
HARIC = {'static', 'auth.cikis'}


def test_tum_get_sayfalari_500_vermiyor(app, authed_client, admin_user):
    """Admin oturumuyla tum parametresiz GET rotalari 500 vermemeli."""
    rotalar = [
        r for r in app.url_map.iter_rules()
        if 'GET' in r.methods
        and '<' not in str(r.rule)        # parametreli rotalari atla
        and r.endpoint not in HARIC
        and not r.endpoint.startswith('static')
    ]

    hatalar = []
    for r in sorted(rotalar, key=lambda x: x.rule):
        try:
            resp = authed_client.get(r.rule, follow_redirects=False)
            if resp.status_code >= 500:
                # 500'de hata satirini yakala
                metin = resp.get_data(as_text=True)
                ipucu = ''
                for satir in metin.split('\n'):
                    if 'Error' in satir or 'Exception' in satir:
                        ipucu = satir.strip()[:160]
                        break
                hatalar.append(f'{r.rule} [{resp.status_code}] {ipucu}')
        except Exception as e:
            hatalar.append(f'{r.rule} [EXC] {type(e).__name__}: {e}')

    assert not hatalar, (
        f'{len(hatalar)} sayfa hata veriyor:\n  '
        + '\n  '.join(hatalar)
    )


def test_smoke_en_az_rota_kapsami(app, authed_client, admin_user):
    """Smoke testin gercekten anlamli sayida rotayi gezdiginden emin ol."""
    rotalar = [
        r for r in app.url_map.iter_rules()
        if 'GET' in r.methods and '<' not in str(r.rule)
        and r.endpoint not in HARIC
        and not r.endpoint.startswith('static')
    ]
    assert len(rotalar) >= 50, (
        f'Sadece {len(rotalar)} GET rotasi bulundu — smoke kapsami '
        f'beklenenden dar, rota kaydinda sorun olabilir.'
    )
