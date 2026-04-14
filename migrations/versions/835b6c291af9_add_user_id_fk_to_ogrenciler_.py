"""add user_id FK to ogrenciler personeller veli_bilgileri

Revision ID: 835b6c291af9
Revises: 5d3b5908a15a
Create Date: 2026-04-14 04:17:05.697276

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '835b6c291af9'
down_revision = '5d3b5908a15a'
branch_labels = None
depends_on = None


def _column_exists(table, column):
    """Kolon var mi kontrol et (PostgreSQL + SQLite uyumlu)."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = [c['name'] for c in inspector.get_columns(table)]
    return column in columns


def upgrade():
    for table in ('ogrenciler', 'personeller', 'veli_bilgileri'):
        if not _column_exists(table, 'user_id'):
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
                batch_op.create_unique_constraint(f'uq_{table}_user_id', ['user_id'])
                batch_op.create_foreign_key(f'fk_{table}_user_id', 'users', ['user_id'], ['id'])


def downgrade():
    for table in ('veli_bilgileri', 'personeller', 'ogrenciler'):
        if _column_exists(table, 'user_id'):
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.drop_constraint(f'fk_{table}_user_id', type_='foreignkey')
                batch_op.drop_constraint(f'uq_{table}_user_id', type_='unique')
                batch_op.drop_column('user_id')
