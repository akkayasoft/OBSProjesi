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


# Turkce ay adlari (backfill icin)
_AY_ADLARI_TR = [
    'Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran',
    'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık',
]


def _surucu_donem_backfill(conn):
    """Surucu kursu tenant'i icin: donemi olmayan kursiyerlere
    kayit_tarihi'ne gore donem olustur ve ata. Idempotent.

    Mevcut kursiyerlerin (yil, ay) kombinasyonlarini bulur, eksik
    olanlari surucu_donemler tablosuna ekler, sonra UPDATE ile
    kursiyerlere donem_id atar.
    """
    import calendar as _cal
    # 1) Eksik (yil, ay) ciftlerini bul
    rows = conn.execute(text("""
        SELECT DISTINCT EXTRACT(YEAR FROM kayit_tarihi)::int AS yil,
                        EXTRACT(MONTH FROM kayit_tarihi)::int AS ay
          FROM kursiyerler
         WHERE kayit_tarihi IS NOT NULL
           AND donem_id IS NULL
    """)).fetchall()
    for yil, ay in rows:
        # Olusturmaya calis (idempotent — UNIQUE varsa hata)
        ad = f'{_AY_ADLARI_TR[ay - 1]} {yil}'
        baslangic = f'{yil:04d}-{ay:02d}-01'
        son_gun = _cal.monthrange(yil, ay)[1]
        bitis = f'{yil:04d}-{ay:02d}-{son_gun:02d}'
        try:
            conn.execute(text("""
                INSERT INTO surucu_donemler
                    (yil, ay, ad, baslangic_tarihi, bitis_tarihi,
                     durum, olusturma_tarihi)
                VALUES (:yil, :ay, :ad, :bas, :bit, 'aktif', NOW())
                ON CONFLICT (yil, ay) DO NOTHING
            """), dict(yil=yil, ay=ay, ad=ad, bas=baslangic, bit=bitis))
        except Exception:
            pass
    # 2) UPDATE ile donemi olmayan kursiyerlere ata
    conn.execute(text("""
        UPDATE kursiyerler k
           SET donem_id = d.id
          FROM surucu_donemler d
         WHERE k.donem_id IS NULL
           AND k.kayit_tarihi IS NOT NULL
           AND EXTRACT(YEAR FROM k.kayit_tarihi)::int = d.yil
           AND EXTRACT(MONTH FROM k.kayit_tarihi)::int = d.ay
    """))


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


@tenant_cli.command('create-all-tables')
def create_all_tables_cmd():
    """Tum aktif tenant DB'lerinde db.metadata.create_all() + bilinen
    ALTER TABLE backfill'lerini calistirir.

    Idempotent. Yeni model eklendiginde Alembic migration yazilana
    kadar hizli kapatma olarak deploy.sh'da kullanilir.
    """
    # Flask uygulama context'i icinde olmaliyiz ki db.metadata tum
    # modelleri tanisin (create_app modelleri import ediyor).
    from app.extensions import db
    from .engines import get_tenant_engine

    # Mevcut tablolara sonradan eklenen kolonlar — idempotent ALTER.
    # Postgres 9.6+ ADD COLUMN IF NOT EXISTS destekler. Tablo yoksa
    # exception silently atlanir.
    TENANT_KOLON_BACKFILL = [
        # surucu kursu
        ('kursiyerler', 'tc_kimlik', 'VARCHAR(11)'),
        ('kursiyerler', 'donem_id', 'INTEGER'),
        ('surucu_sinav_harci_kayitlari', 'gelir_gider_kayit_id', 'INTEGER'),
        ('kursiyer_taksitleri', 'gelir_gider_kayit_id', 'INTEGER'),
        # Faz 3.A — odeme detaylari + makbuz
        ('kursiyer_taksitleri', 'odeme_turu', 'VARCHAR(20)'),
        ('kursiyer_taksitleri', 'odeyen_ad', 'VARCHAR(150)'),
        ('kursiyer_taksitleri', 'teslim_alan_id', 'INTEGER'),
        ('kursiyer_taksitleri', 'makbuz_no', 'VARCHAR(50)'),
        # Sinav harc makbuz alanlari (kursiyer taksitiyle ayni desen)
        ('surucu_sinav_harci_kayitlari', 'odeme_turu', 'VARCHAR(20)'),
        ('surucu_sinav_harci_kayitlari', 'odeyen_ad', 'VARCHAR(150)'),
        ('surucu_sinav_harci_kayitlari', 'teslim_alan_id', 'INTEGER'),
        ('surucu_sinav_harci_kayitlari', 'makbuz_no', 'VARCHAR(50)'),
        # OBS muhasebe — odeme alinca otomatik gelir kaydi linklemesi
        ('odemeler', 'gelir_gider_kayit_id', 'INTEGER'),
        # Personel maas odemesi -> Gider linki
        ('personel_odeme_kayitlari', 'gelir_gider_kayit_id', 'INTEGER'),
        # Kantin satisi -> Gelir linki
        ('kantin_satislar', 'gelir_gider_kayit_id', 'INTEGER'),
    ]

    with master_session() as s:
        tenantler = s.execute(
            select(Tenant).where(Tenant.durum == 'aktif')
        ).scalars().all()
        for t in tenantler:
            s.expunge(t)

    hata = 0
    for t in tenantler:
        try:
            engine = get_tenant_engine(t.db_name)
            db.metadata.create_all(bind=engine)
            # ALTER TABLE backfill — tablonun mevcut oldugu durumlarda
            # eksik kolonlari ekler. Yoksa tablo, except'e dusup atlanir.
            with engine.begin() as conn:
                for tablo, kolon, tip in TENANT_KOLON_BACKFILL:
                    try:
                        conn.execute(text(
                            f'ALTER TABLE {tablo} '
                            f'ADD COLUMN IF NOT EXISTS {kolon} {tip}'
                        ))
                    except Exception as alter_err:
                        # tablo henuz yoksa veya baska beklenmedik durum
                        # — sessizce gec
                        pass
                # Surucu kursu donem backfill - donemi olmayan
                # kursiyerlere kayit_tarihi'ne gore donem ata. Idempotent.
                if t.kurum_tipi == 'surucu_kursu':
                    try:
                        _surucu_donem_backfill(conn)
                    except Exception:
                        pass
            click.echo(f'  ok  {t.slug} ({t.db_name})')
        except Exception as e:
            hata += 1
            click.echo(f'  ERR {t.slug}: {e}', err=True)
    if hata:
        raise click.ClickException(f'{hata} tenant icin create_all basarisiz.')
    click.echo(f'\n{len(tenantler)} tenant DB icin create_all + backfill tamamlandi.')


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


@tenant_cli.command('create-admin')
@click.argument('username')
@click.option('--ad', required=True)
@click.option('--soyad', required=True)
@click.option('--email')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True,
              help='Sifre (girilince soruluyor, gorunmuyor)')
def create_platform_admin_cmd(username, ad, soyad, email, password):
    """Yeni platform admin (sistem yoneticisi) olustur.

    Bu hesap tenant'lardan bagimsizdir ve /sistem/giris uzerinden
    girip tum tenant'lari yonetir.

    Ornek:
        flask tenant create-admin akkaya --ad Ayhan --soyad Akkaya
    """
    from app.tenancy.models import PlatformAdmin

    with master_session() as s:
        mevcut = s.execute(
            select(PlatformAdmin).where(PlatformAdmin.username == username)
        ).scalar_one_or_none()
        if mevcut:
            raise click.ClickException(f'Bu kullanici adi zaten var: {username}')

        admin = PlatformAdmin(
            username=username, ad=ad, soyad=soyad, email=email, aktif=True,
        )
        admin.set_password(password)
        s.add(admin)
        s.commit()
        click.echo(f'✓ Platform admin olusturuldu: {username} ({ad} {soyad})')
        click.echo('  Giris: /sistem/giris')


@tenant_cli.command('list-admins')
def list_platform_admins_cmd():
    """Tum platform adminlerini listele."""
    from app.tenancy.models import PlatformAdmin

    with master_session() as s:
        adminler = s.execute(select(PlatformAdmin).order_by(PlatformAdmin.id)).scalars().all()
        if not adminler:
            click.echo('(hic platform admin yok — once create-admin calistir)')
            return
        for a in adminler:
            durum = '✓ aktif' if a.aktif else '✗ pasif'
            son = a.son_giris.strftime('%d.%m.%Y %H:%M') if a.son_giris else 'hic'
            click.echo(f'  {a.username:20s} {a.tam_ad:30s} {durum:10s} son giris: {son}')


@tenant_cli.command('reset-admin-password')
@click.argument('username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
def reset_platform_admin_password_cmd(username, password):
    """Platform admin sifresini sifirla."""
    from app.tenancy.models import PlatformAdmin

    with master_session() as s:
        admin = s.execute(
            select(PlatformAdmin).where(PlatformAdmin.username == username)
        ).scalar_one_or_none()
        if not admin:
            raise click.ClickException(f'Admin yok: {username}')
        admin.set_password(password)
        s.commit()
        click.echo(f'✓ {username} sifresi guncellendi.')


def register_cli(app):
    app.cli.add_command(tenant_cli)
