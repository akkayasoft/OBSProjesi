"""ozel bildirim: sablon + gonderim log tablolari (idempotent)

Revision ID: b82e4f1c5a90
Revises: a7c4e0b3f91d
Create Date: 2026-04-19 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b82e4f1c5a90'
down_revision = 'a7c4e0b3f91d'
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade():
    if not _has_table('bildirim_sablonlari'):
        op.create_table(
            'bildirim_sablonlari',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('ad', sa.String(length=100), nullable=False),
            sa.Column('baslik', sa.String(length=200), nullable=False),
            sa.Column('mesaj', sa.Text(), nullable=False),
            sa.Column('kategori', sa.String(length=30), nullable=False,
                      server_default='genel'),
            sa.Column('link', sa.String(length=500), nullable=True),
            sa.Column('sistem', sa.Boolean(), nullable=True,
                      server_default=sa.text('false')),
            sa.Column('aktif', sa.Boolean(), nullable=False,
                      server_default=sa.text('true')),
            sa.Column('olusturan_id', sa.Integer(),
                      sa.ForeignKey('users.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    if not _has_table('bildirim_gonderimleri'):
        op.create_table(
            'bildirim_gonderimleri',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('gonderen_id', sa.Integer(),
                      sa.ForeignKey('users.id'), nullable=False),
            sa.Column('sablon_id', sa.Integer(),
                      sa.ForeignKey('bildirim_sablonlari.id'), nullable=True),
            sa.Column('baslik', sa.String(length=200), nullable=False),
            sa.Column('mesaj', sa.Text(), nullable=False),
            sa.Column('kategori', sa.String(length=30), nullable=False,
                      server_default='genel'),
            sa.Column('link', sa.String(length=500), nullable=True),
            sa.Column('alici_sayisi', sa.Integer(), nullable=False,
                      server_default='0'),
            sa.Column('push_basarili', sa.Integer(), nullable=False,
                      server_default='0'),
            sa.Column('kaynak', sa.String(length=30), nullable=False,
                      server_default='manuel'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )


def downgrade():
    if _has_table('bildirim_gonderimleri'):
        op.drop_table('bildirim_gonderimleri')
    if _has_table('bildirim_sablonlari'):
        op.drop_table('bildirim_sablonlari')
