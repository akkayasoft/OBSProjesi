"""`flask tenant ...` CLI komutlari.

Komutlar:
    flask tenant init-master
        Master DB'de tenants tablosunu olusturur.

    flask tenant create <slug> --ad "..." [--db-name ...] [--create-db]
        Tenant kaydi ekler. --create-db ile Postgres'te ayrica yeni bir DB
        olusturur ve ona migration'lari uygular.

    flask tenant list
        Tum tenant'lari listeler.

    flask tenant migrate-all
        Tum aktif tenant'lar icin `flask db upgrade` calistirir.

    flask tenant set-status <slug> <aktif|askida>
"""
import os
import subprocess
import sys

import click
from flask import current_app
from flask.cli import AppGroup
from sqlalchemy import text, select

from .master import master_session, create_master_tables, get_master_engine
from .models import Tenant


tenant_cli = AppGroup('tenant', help='Multi-tenant yonetim komutlari.')


def _slugify(s: str) -> str:
    out = []
    for ch in s.lower():
        if ch.isalnum() or ch == '-':
            out.append(ch)
        elif ch in (' ', '_'):
            out.append('-')
    return ''.join(out).strip('-') or 'tenant'


def _default_db_name(slug: str) -> str:
    return 'obs_' + slug.replace('-', '_')


def _admin_psql_url() -> str:
    """Postgres admin baglantisi (CREATE DATABASE icin)."""
    url = current_app.config.get('TENANT_ADMIN_DATABASE_URL') or \
        current_app.config.get('MASTER_DATABASE_URL')
    if not url:
        raise click.ClickException(
            'TENANT_ADMIN_DATABASE_URL veya MASTER_DATABASE_URL tanimli '
            'olmali (ayni sunucuya baglanip CREATE DATABASE icin).'
        )
    return url


@tenant_cli.command('init-master')
def init_master_cmd():
    """Master DB'de tenants tablosunu olustur."""
    create_master_tables()
    click.echo('✓ Master DB tablolari hazir.')


@tenant_cli.command('list')
def list_cmd():
    """Tum tenantlari listele."""
    with master_session() as s:
        rows = s.execute(select(Tenant).order_by(Tenant.slug)).scalars().all()
    if not rows:
        click.echo('(hic tenant yok)')
        return
    click.echo(f'{"slug":<20} {"db_name":<24} {"durum":<10} {"bitis":<12} ad')
    click.echo('-' * 80)
    for t in rows:
        bitis = t.abonelik_bitis.isoformat() if t.abonelik_bitis else '—'
        click.echo(f'{t.slug:<20} {t.db_name:<24} {t.durum:<10} {bitis:<12} {t.ad}')


@tenant_cli.command('create')
@click.argument('slug')
@click.option('--ad', required=True, help='Kurum adi (ornek: "X Dershane").')
@click.option('--db-name', default=None, help='Postgres DB adi (vars: obs_<slug>).')
@click.option('--create-db/--no-create-db', default=False,
              help='Postgres uzerinde yeni DB olustur + migration uygula.')
@click.option('--email', default=None, help='Iletisim email.')
def create_cmd(slug, ad, db_name, create_db, email):
    """Yeni tenant ekle (ve istersen DB'sini de yarat)."""
    slug = _slugify(slug)
    db_name = db_name or _default_db_name(slug)

    with master_session() as s:
        mevcut = s.execute(
            select(Tenant).where(Tenant.slug == slug)
        ).scalar_one_or_none()
        if mevcut:
            raise click.ClickException(f'slug zaten mevcut: {slug}')
        t = Tenant(slug=slug, ad=ad, db_name=db_name,
                   durum='aktif', iletisim_email=email)
        s.add(t)
        s.commit()
        click.echo(f'✓ Tenant eklendi: {slug} (db={db_name})')

    if create_db:
        # 1) CREATE DATABASE
        admin_engine = get_master_engine()
        with admin_engine.connect() as conn:
            conn.execute(text('COMMIT'))  # autocommit icin
            exists = conn.execute(
                text('SELECT 1 FROM pg_database WHERE datname=:n'),
                {'n': db_name}
            ).first()
            if exists:
                click.echo(f'  (DB zaten var: {db_name})')
            else:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                click.echo(f'  ✓ DB olusturuldu: {db_name}')

        # 2) Migration uygula: alt-process ile `flask db upgrade`, DB URL
        # override ederek.
        from .engines import _build_url
        url = _build_url(db_name)
        env = os.environ.copy()
        env['DATABASE_URL'] = url
        env['MULTITENANT_ENABLED'] = '0'  # migration sirasinda middleware devre disi
        click.echo(f'  flask db upgrade -> {db_name} ...')
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'db', 'upgrade'],
            env=env, capture_output=True, text=True,
        )
        if result.returncode != 0:
            click.echo(result.stdout)
            click.echo(result.stderr, err=True)
            raise click.ClickException('Migration basarisiz.')
        click.echo('  ✓ Migration tamamlandi.')


@tenant_cli.command('migrate-all')
def migrate_all_cmd():
    """Tum aktif tenant'lar icin migration calistir."""
    with master_session() as s:
        tenantler = s.execute(
            select(Tenant).where(Tenant.durum == 'aktif')
        ).scalars().all()
        for t in tenantler:
            s.expunge(t)

    from .engines import _build_url
    hata = 0
    for t in tenantler:
        url = _build_url(t.db_name)
        env = os.environ.copy()
        env['DATABASE_URL'] = url
        env['MULTITENANT_ENABLED'] = '0'
        click.echo(f'-> {t.slug} ({t.db_name})')
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'db', 'upgrade'],
            env=env, capture_output=True, text=True,
        )
        if result.returncode != 0:
            hata += 1
            click.echo(f'  HATA:\n{result.stderr}', err=True)
        else:
            click.echo('  ✓ OK')
    if hata:
        raise click.ClickException(f'{hata} tenant migration basarisiz.')


@tenant_cli.command('seed-all')
def seed_all_cmd():
    """Tum aktif tenant'lar icin `flask seed` calistir (idempotent)."""
    with master_session() as s:
        tenantler = s.execute(
            select(Tenant).where(Tenant.durum == 'aktif')
        ).scalars().all()
        for t in tenantler:
            s.expunge(t)

    from .engines import _build_url
    hata = 0
    for t in tenantler:
        url = _build_url(t.db_name)
        env = os.environ.copy()
        env['DATABASE_URL'] = url
        env['MULTITENANT_ENABLED'] = '0'
        click.echo(f'-> {t.slug} ({t.db_name})')
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'seed'],
            env=env, capture_output=True, text=True,
        )
        if result.returncode != 0:
            hata += 1
            click.echo(f'  HATA:\n{result.stderr}', err=True)
        else:
            click.echo(f'  ✓ {result.stdout.strip().splitlines()[-1] if result.stdout else "OK"}')
    if hata:
        raise click.ClickException(f'{hata} tenant seed basarisiz.')


@tenant_cli.command('set-status')
@click.argument('slug')
@click.argument('durum', type=click.Choice(['aktif', 'askida', 'silindi']))
def set_status_cmd(slug, durum):
    with master_session() as s:
        t = s.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()
        if not t:
            raise click.ClickException(f'Tenant yok: {slug}')
        t.durum = durum
        s.commit()
        click.echo(f'✓ {slug} durumu: {durum}')


def register_cli(app):
    app.cli.add_command(tenant_cli)
