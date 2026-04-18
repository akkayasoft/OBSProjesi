"""Tum url_for() cagrilarini tara, kirik endpointleri bul."""
from dotenv import load_dotenv; load_dotenv()
from app import create_app
import re, os, glob

app = create_app()
valid_endpoints = {r.endpoint for r in app.url_map.iter_rules()}

pattern = re.compile(r"url_for\(\s*['\"]([\w\.]+)['\"]")

bulunan = {}
for root, _, files in os.walk('app/templates'):
    for f in files:
        if not f.endswith('.html'):
            continue
        path = os.path.join(root, f)
        with open(path, encoding='utf-8') as fh:
            for i, line in enumerate(fh, 1):
                for m in pattern.finditer(line):
                    ep = m.group(1)
                    if ep not in valid_endpoints:
                        bulunan.setdefault(ep, []).append((path, i))

for path in glob.glob('app/**/*.py', recursive=True):
    with open(path, encoding='utf-8') as fh:
        for i, line in enumerate(fh, 1):
            for m in pattern.finditer(line):
                ep = m.group(1)
                if ep not in valid_endpoints:
                    bulunan.setdefault(ep, []).append((path, i))

if bulunan:
    print(f"{len(bulunan)} KIRIK url_for BULUNDU:")
    for ep, yerler in sorted(bulunan.items()):
        print(f"\n  {ep}")
        for p, ln in yerler[:3]:
            print(f"    {p}:{ln}")
        if len(yerler) > 3:
            print(f"    ... ve {len(yerler)-3} daha")
else:
    print("Tum url_for cagrilari gecerli endpoint gosteriyor.")
