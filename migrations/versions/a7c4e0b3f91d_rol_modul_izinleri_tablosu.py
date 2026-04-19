"""rol_modul_izinleri tablosu (idempotent — mevcut DB'lerde sessizce atlar)

Revision ID: a7c4e0b3f91d
Revises: 42f515f2d2e7
Create Date: 2026-04-19 13:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a7c4e0b3f91d'
down_revision = '42f515f2d2e7'
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade():
    # Default DB'de tablo manuel olarak olusturulmustu (migration'a commit
    # edilmeden once). Yeni tenant'larda tablo yok — burada olusturulur.
    if _has_table('rol_modul_izinleri'):
        return

    op.create_table(
        'rol_modul_izinleri',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('rol', sa.String(length=20), nullable=False),
        sa.Column('modul_key', sa.String(length=50), nullable=False),
        sa.Column('aktif', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('rol', 'modul_key', name='uq_rol_modul'),
    )


def downgrade():
    if _has_table('rol_modul_izinleri'):
        op.drop_table('rol_modul_izinleri')
