"""Allow multiple teachers per extra class subject

Revision ID: 25cc1e0220aa
Revises: b87cc835186f
Create Date: 2026-09-20 11:34:12.472623
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "25cc1e0220aa"
down_revision = "b87cc835186f"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("extra_class_subjects", schema=None) as batch_op:

        # A teacher must be assigned to exactly one Extra Class subject.
        batch_op.alter_column(
            "teacher_id",
            existing_type=sa.BIGINT(),
            nullable=False
        )

        # Remove the old rule:
        # one subject can only have one Extra Class teacher.
        batch_op.drop_constraint(
            "unique_extra_class_subject",
            type_="unique"
        )

        # New rule:
        # one teacher can only have one Extra Class subject.
        batch_op.create_unique_constraint(
            "uq_extra_class_teacher_subject",
            ["teacher_id"]
        )


def downgrade():
    with op.batch_alter_table("extra_class_subjects", schema=None) as batch_op:

        # Remove the new teacher uniqueness rule.
        batch_op.drop_constraint(
            "uq_extra_class_teacher_subject",
            type_="unique"
        )

        # Restore the previous rule.
        batch_op.create_unique_constraint(
            "unique_extra_class_subject",
            ["subject_id"]
        )

        # Restore nullable teacher_id.
        batch_op.alter_column(
            "teacher_id",
            existing_type=sa.BIGINT(),
            nullable=True
        )