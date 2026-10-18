"""Make extra-class semesters teacher/class specific.

Revision ID: 742c9f7b1e23
Revises: 741c0fec32ec
"""

from alembic import op
import sqlalchemy as sa


revision = "742c9f7b1e23"
down_revision = "741c0fec32ec"
branch_labels = None
depends_on = None


def upgrade():
    # Existing installations may still contain the old global semester
    # rows. The column is therefore introduced nullable first so the
    # migration is safe. New teacher-created semesters always supply it.
    op.add_column(
        "extra_class_terms",
        sa.Column("extra_class_subject_id", sa.BigInteger(), nullable=True),
    )

    op.create_index(
        "ix_extra_class_terms_extra_class_subject_id",
        "extra_class_terms",
        ["extra_class_subject_id"],
    )

    op.create_foreign_key(
        "fk_extra_class_terms_extra_class_subject_id",
        "extra_class_terms",
        "extra_class_subjects",
        ["extra_class_subject_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade():
    op.drop_constraint(
        "fk_extra_class_terms_extra_class_subject_id",
        "extra_class_terms",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_extra_class_terms_extra_class_subject_id",
        table_name="extra_class_terms",
    )
    op.drop_column("extra_class_terms", "extra_class_subject_id")
