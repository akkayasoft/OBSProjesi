"""kullanici bazli modul izinleri ve yonetici rolu

Revision ID: 7a2b1c9f4e50
Revises: a3d7e9c1f4b2
Create Date: 2026-04-11 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a2b1c9f4e50'
down_revision = 'a3d7e9c1f4b2'
branch_labels = None
depends_on = None


def upgrade():
    # Kullanici bazli modul izinleri tablosu (yonetici rolu icin)
    op.create_table(
        'kullanici_modul_izinleri',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('modul_key', sa.String(length=50), nullable=False),
        sa.Column('aktif', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('olusturma_tarihi', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'modul_key', name='uq_kullanici_modul'),
    )
    # Arama hizi icin index
    op.create_index(
        'ix_kullanici_modul_izinleri_user_id',
        'kullanici_modul_izinleri',
        ['user_id'],
    )


def downgrade():
    op.drop_index('ix_kullanici_modul_izinleri_user_id', table_name='kullanici_modul_izinleri')
    op.drop_table('kullanici_modul_izinleri')
