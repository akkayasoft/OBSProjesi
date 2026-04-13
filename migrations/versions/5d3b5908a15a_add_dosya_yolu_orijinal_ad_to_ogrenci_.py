"""add dosya_yolu orijinal_ad to ogrenci_belgeleri

Revision ID: 5d3b5908a15a
Revises: 7a2b1c9f4e50
Create Date: 2026-04-13 21:47:27.375988

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d3b5908a15a'
down_revision = '7a2b1c9f4e50'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    """Kolon var mi kontrol et (PostgreSQL + SQLite uyumlu)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table)]
    return column in columns


def upgrade():
    # ogrenci_belgeleri tablosuna eksik kolonlari ekle
    # (Model'de vardi ama ilk migration'da olusturulmamisti)
    # Local SQLite'da create_all zaten ekledi, VPS PostgreSQL'de yok
    if not _column_exists('ogrenci_belgeleri', 'dosya_yolu'):
        op.add_column('ogrenci_belgeleri',
                      sa.Column('dosya_yolu', sa.String(length=300), nullable=True))
    if not _column_exists('ogrenci_belgeleri', 'orijinal_ad'):
        op.add_column('ogrenci_belgeleri',
                      sa.Column('orijinal_ad', sa.String(length=255), nullable=True))


def downgrade():
    if _column_exists('ogrenci_belgeleri', 'orijinal_ad'):
        op.drop_column('ogrenci_belgeleri', 'orijinal_ad')
    if _column_exists('ogrenci_belgeleri', 'dosya_yolu'):
        op.drop_column('ogrenci_belgeleri', 'dosya_yolu')
