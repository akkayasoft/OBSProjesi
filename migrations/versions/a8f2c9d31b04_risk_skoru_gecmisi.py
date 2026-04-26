"""risk skoru gecmisi (haftalik snapshot)

Revision ID: a8f2c9d31b04
Revises: 21026d8e7508
Create Date: 2026-04-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8f2c9d31b04'
down_revision = '21026d8e7508'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'risk_skoru_gecmisi',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ogrenci_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_tarih', sa.Date(), nullable=False),
        sa.Column('skor', sa.Integer(), nullable=False),
        sa.Column('seviye', sa.String(length=10), nullable=False),
        sa.Column('devamsizlik_gun', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('olumsuz_davranis', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('deneme_trend', sa.String(length=20), nullable=True),
        sa.Column('sebepler', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ogrenci_id'], ['ogrenciler.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ogrenci_id', 'snapshot_tarih',
                            name='uq_risk_gecmisi_ogrenci_tarih'),
    )
    op.create_index('ix_risk_gecmisi_tarih', 'risk_skoru_gecmisi',
                    ['snapshot_tarih'], unique=False)


def downgrade():
    op.drop_index('ix_risk_gecmisi_tarih', table_name='risk_skoru_gecmisi')
    op.drop_table('risk_skoru_gecmisi')
