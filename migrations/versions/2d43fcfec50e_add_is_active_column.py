"""add is_active column


Revision ID: 2d43fcfec50e
Revises: 75f59a4a0dfe
Create Date: 2026-06-06 10:40:05.662329

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d43fcfec50e'
down_revision = '75f59a4a0dfe'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(
            sa.Column(
                'is_active',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('true')
            )
        )


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('is_active')