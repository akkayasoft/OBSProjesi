"""Uygulama Kilavuzu - icerigi docs/kullanim-kilavuzu/ klasorunden okur,
markdown -> HTML donusum yapar, sayfalar arasi navigasyonla gosterir.

Sadece dosya sisteminden okuyor — DB, model gerektirmez. Resimler
docs/kullanim-kilavuzu/gorseller/ klasorunden serve edilir.
"""
import os
import re
from flask import (Blueprint, render_template, abort, send_from_directory,
                   current_app, url_for)
from flask_login import login_required

bp = Blueprint('kilavuz', __name__, url_prefix='/kilavuz')


def _kilavuz_dir() -> str:
    """docs/kullanim-kilavuzu/ klasorunun mutlak yolu."""
    # app/ayarlar/routes/kilavuz.py -> proje koku 3 seviye yukari
    return os.path.normpath(os.path.join(
        os.path.dirname(__file__), '..', '..', '..',
        'docs', 'kullanim-kilavuzu',
    ))


def _bolum_listesi():
    """Kilavuz md dosyalarini sirayla dondur. Her oge dict:
    {slug, no, baslik, dosya}
    """
    base = _kilavuz_dir()
    if not os.path.isdir(base):
        return []
    items = []
    for fn in sorted(os.listdir(base)):
        if not fn.endswith('.md'):
            continue
        # 00-index.md, 01-giris.md gibi
        m = re.match(r'^(\d{2})-(.+)\.md$', fn)
        if not m:
            continue
        no, slug = m.group(1), m.group(2)
        # H1 basligini ilk satirdan al
        path = os.path.join(base, fn)
        baslik = slug.replace('-', ' ').title()
        try:
            with open(path, 'r', encoding='utf-8') as f:
                first = f.readline().strip()
                if first.startswith('# '):
                    baslik = first[2:].strip()
                    # '1. Sisteme Giris' -> 'Sisteme Giris' (numarayi at)
                    baslik = re.sub(r'^\d+\.\s*', '', baslik)
        except Exception:
            pass
        items.append({
            'slug': f'{no}-{slug}',
            'no': int(no),
            'baslik': baslik,
            'dosya': fn,
        })
    return items


def _md_to_html(content: str) -> str:
    """Markdown -> HTML. Resim path'lerini Flask url'sine cevirir."""
    import markdown as _md
    # Linkleri ve resimleri kilavuz icindeki rotalara map et
    # gorseller/xxx.png -> /ayarlar/kilavuz/gorsel/xxx.png
    html = _md.markdown(
        content,
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'],
        output_format='html5',
    )
    # Resim path'lerini guncelle
    html = re.sub(
        r'src="gorseller/([^"]+)"',
        lambda m: f'src="{url_for("ayarlar.kilavuz.gorsel", filename=m.group(1))}"',
        html,
    )
    # Diger md dosyalarina linkler -> /ayarlar/kilavuz/<slug>
    def _link_repl(m):
        target = m.group(1)
        if target.startswith('http://') or target.startswith('https://'):
            return m.group(0)
        if target == '00-index.md':
            return f'href="{url_for("ayarlar.kilavuz.index")}"'
        m2 = re.match(r'^(\d{2}-[\w-]+)\.md$', target)
        if m2:
            return f'href="{url_for("ayarlar.kilavuz.bolum", slug=m2.group(1))}"'
        return m.group(0)
    html = re.sub(r'href="([^"]+)"', _link_repl, html)
    return html


@bp.route('/')
@login_required
def index():
    """Kilavuz icindekiler sayfasi (00-index.md icerigi)."""
    base = _kilavuz_dir()
    index_path = os.path.join(base, '00-index.md')
    if not os.path.isfile(index_path):
        abort(404)
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    html = _md_to_html(content)
    bolumler = _bolum_listesi()
    # 00-index'i listeden cikar (zaten o sayfadayiz)
    bolumler = [b for b in bolumler if not b['slug'].startswith('00-')]
    return render_template(
        'ayarlar/kilavuz/index.html',
        icerik_html=html,
        bolumler=bolumler,
    )


@bp.route('/<slug>')
@login_required
def bolum(slug):
    """Tek bir bolum sayfasi."""
    base = _kilavuz_dir()
    # Slug formati: 01-giris, 02-anasayfa vs.
    if not re.match(r'^\d{2}-[\w-]+$', slug):
        abort(404)
    path = os.path.join(base, f'{slug}.md')
    if not os.path.isfile(path):
        abort(404)
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    html = _md_to_html(content)

    # Onceki / sonraki
    bolumler = [b for b in _bolum_listesi() if not b['slug'].startswith('00-')]
    cur_idx = next((i for i, b in enumerate(bolumler) if b['slug'] == slug), None)
    onceki = bolumler[cur_idx - 1] if cur_idx and cur_idx > 0 else None
    sonraki = (bolumler[cur_idx + 1]
               if cur_idx is not None and cur_idx + 1 < len(bolumler)
               else None)
    return render_template(
        'ayarlar/kilavuz/bolum.html',
        icerik_html=html,
        bolum_slug=slug,
        bolumler=bolumler,
        cur_idx=cur_idx,
        onceki=onceki,
        sonraki=sonraki,
    )


@bp.route('/gorsel/<path:filename>')
@login_required
def gorsel(filename):
    """Kilavuz icindeki resimleri serve et (docs/.../gorseller/)."""
    base = _kilavuz_dir()
    gorsel_dir = os.path.join(base, 'gorseller')
    return send_from_directory(gorsel_dir, filename)
