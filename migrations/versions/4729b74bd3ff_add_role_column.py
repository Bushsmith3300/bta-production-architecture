"""add role column

Revision ID: 4729b74bd3ff
Revises: ea5250f84682
Create Date: 2026-06-04 10:50:22.402224
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4729b74bd3ff'
down_revision = 'ea5250f84682'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'role',
                sa.String(length=20),
                nullable=False,
                server_default='student'
            )
        )


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('role')