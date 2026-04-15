"""add indirim fields to odeme_planlari

Revision ID: d6a3b9377c5e
Revises: 835b6c291af9
Create Date: 2026-04-15 11:11:36.153146

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd6a3b9377c5e'
down_revision = '835b6c291af9'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table)]
    return column in columns


def upgrade():
    with op.batch_alter_table('odeme_planlari', schema=None) as batch_op:
        if not _column_exists('odeme_planlari', 'indirim_tutar'):
            batch_op.add_column(sa.Column('indirim_tutar', sa.Numeric(precision=12, scale=2), nullable=True))
        if not _column_exists('odeme_planlari', 'indirim_aciklama'):
            batch_op.add_column(sa.Column('indirim_aciklama', sa.String(length=200), nullable=True))


def downgrade():
    with op.batch_alter_table('odeme_planlari', schema=None) as batch_op:
        if _column_exists('odeme_planlari', 'indirim_aciklama'):
            batch_op.drop_column('indirim_aciklama')
        if _column_exists('odeme_planlari', 'indirim_tutar'):
            batch_op.drop_column('indirim_tutar')
