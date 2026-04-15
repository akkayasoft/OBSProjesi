"""add tahsilat actions (cancel, restructure, postpone)

Revision ID: 21332d5baabd
Revises: d6a3b9377c5e
Create Date: 2026-04-15 15:10:24.900510

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '21332d5baabd'
down_revision = 'd6a3b9377c5e'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table)]
    return column in columns


def upgrade():
    with op.batch_alter_table('odeme_planlari', schema=None) as batch_op:
        if not _column_exists('odeme_planlari', 'durum'):
            batch_op.add_column(sa.Column('durum', sa.String(length=20), nullable=True,
                                          server_default='aktif'))
        if not _column_exists('odeme_planlari', 'kapanma_tarihi'):
            batch_op.add_column(sa.Column('kapanma_tarihi', sa.DateTime(), nullable=True))
        if not _column_exists('odeme_planlari', 'kapanma_nedeni'):
            batch_op.add_column(sa.Column('kapanma_nedeni', sa.String(length=200), nullable=True))
        if not _column_exists('odeme_planlari', 'onceki_plan_id'):
            batch_op.add_column(sa.Column('onceki_plan_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_odeme_planlari_onceki_plan_id',
                'odeme_planlari', ['onceki_plan_id'], ['id']
            )

    with op.batch_alter_table('taksitler', schema=None) as batch_op:
        if not _column_exists('taksitler', 'orjinal_vade_tarihi'):
            batch_op.add_column(sa.Column('orjinal_vade_tarihi', sa.Date(), nullable=True))
        if not _column_exists('taksitler', 'erteleme_notu'):
            batch_op.add_column(sa.Column('erteleme_notu', sa.String(length=200), nullable=True))

    with op.batch_alter_table('odemeler', schema=None) as batch_op:
        if not _column_exists('odemeler', 'iptal_edildi'):
            batch_op.add_column(sa.Column('iptal_edildi', sa.Boolean(), nullable=True,
                                          server_default=sa.false()))
        if not _column_exists('odemeler', 'iptal_tarihi'):
            batch_op.add_column(sa.Column('iptal_tarihi', sa.DateTime(), nullable=True))
        if not _column_exists('odemeler', 'iptal_nedeni'):
            batch_op.add_column(sa.Column('iptal_nedeni', sa.String(length=200), nullable=True))
        if not _column_exists('odemeler', 'iptal_eden_id'):
            batch_op.add_column(sa.Column('iptal_eden_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_odemeler_iptal_eden_id',
                'users', ['iptal_eden_id'], ['id']
            )


def downgrade():
    with op.batch_alter_table('odemeler', schema=None) as batch_op:
        if _column_exists('odemeler', 'iptal_eden_id'):
            try:
                batch_op.drop_constraint('fk_odemeler_iptal_eden_id', type_='foreignkey')
            except Exception:
                pass
            batch_op.drop_column('iptal_eden_id')
        if _column_exists('odemeler', 'iptal_nedeni'):
            batch_op.drop_column('iptal_nedeni')
        if _column_exists('odemeler', 'iptal_tarihi'):
            batch_op.drop_column('iptal_tarihi')
        if _column_exists('odemeler', 'iptal_edildi'):
            batch_op.drop_column('iptal_edildi')

    with op.batch_alter_table('taksitler', schema=None) as batch_op:
        if _column_exists('taksitler', 'erteleme_notu'):
            batch_op.drop_column('erteleme_notu')
        if _column_exists('taksitler', 'orjinal_vade_tarihi'):
            batch_op.drop_column('orjinal_vade_tarihi')

    with op.batch_alter_table('odeme_planlari', schema=None) as batch_op:
        if _column_exists('odeme_planlari', 'onceki_plan_id'):
            try:
                batch_op.drop_constraint('fk_odeme_planlari_onceki_plan_id', type_='foreignkey')
            except Exception:
                pass
            batch_op.drop_column('onceki_plan_id')
        if _column_exists('odeme_planlari', 'kapanma_nedeni'):
            batch_op.drop_column('kapanma_nedeni')
        if _column_exists('odeme_planlari', 'kapanma_tarihi'):
            batch_op.drop_column('kapanma_tarihi')
        if _column_exists('odeme_planlari', 'durum'):
            batch_op.drop_column('durum')
