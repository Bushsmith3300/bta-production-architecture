"""Add semester-specific monthly fees for Extra Classes.

Revision ID: 8b71d4a2c9e0
Revises: 742c9f7b1e23
Create Date: 2026-10-09
"""

from alembic import op
import sqlalchemy as sa


revision = "8b71d4a2c9e0"
down_revision = "742c9f7b1e23"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "extra_class_terms",
        sa.Column("monthly_fee", sa.Numeric(12, 2), nullable=True)
    )
    op.create_check_constraint(
        "ck_extra_class_term_monthly_fee",
        "extra_class_terms",
        "monthly_fee IS NULL OR monthly_fee >= 0"
    )


def downgrade():
    op.drop_constraint(
        "ck_extra_class_term_monthly_fee",
        "extra_class_terms",
        type_="check"
    )
    op.drop_column("extra_class_terms", "monthly_fee")
