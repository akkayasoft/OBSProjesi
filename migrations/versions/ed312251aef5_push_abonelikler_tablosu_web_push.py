"""push_abonelikler tablosu (web push)

Revision ID: ed312251aef5
Revises: 21332d5baabd
Create Date: 2026-04-17 10:22:20.129324

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ed312251aef5'
down_revision = '21332d5baabd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'push_abonelikler',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('kullanici_id', sa.Integer(), nullable=False),
        sa.Column('endpoint', sa.Text(), nullable=False),
        sa.Column('p256dh', sa.String(length=255), nullable=False),
        sa.Column('auth', sa.String(length=255), nullable=False),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('aktif', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('son_kullanim', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['kullanici_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('endpoint'),
    )
    with op.batch_alter_table('push_abonelikler', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_push_abonelikler_kullanici_id'),
            ['kullanici_id'], unique=False
        )


def downgrade():
    with op.batch_alter_table('push_abonelikler', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_push_abonelikler_kullanici_id'))
    op.drop_table('push_abonelikler')
