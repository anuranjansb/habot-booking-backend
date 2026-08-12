"""link parents to users

Revision ID: 687fb724826e
Revises: d02070d1bfda
Create Date: 2026-08-12 18:16:19.301707

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '687fb724826e'
down_revision = 'd02070d1bfda'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('parents', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('user_id', sa.Integer(), nullable=True)
        )
        batch_op.create_unique_constraint(None, ['user_id'])
        batch_op.create_foreign_key(
            None,
            'users',
            ['user_id'],
            ['id'],
        )


def downgrade():
    with op.batch_alter_table('parents', schema=None) as batch_op:
        batch_op.drop_constraint(
            None,
            type_='foreignkey',
        )
        batch_op.drop_constraint(
            None,
            type_='unique',
        )
        batch_op.drop_column('user_id')
