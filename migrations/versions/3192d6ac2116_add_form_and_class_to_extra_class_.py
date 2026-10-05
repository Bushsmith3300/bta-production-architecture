"""Add form and class to extra class enrollment

Revision ID: 3192d6ac2116
Revises: 25cc1e0220aa
Create Date: 2026-09-23 20:30:14.422592
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3192d6ac2116"
down_revision = "25cc1e0220aa"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table(
        "extra_class_enrollments",
        schema=None
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "form",
                sa.String(length=20),
                nullable=False
            )
        )

        batch_op.add_column(
            sa.Column(
                "class_name",
                sa.String(length=100),
                nullable=True
            )
        )

        batch_op.create_index(
            "ix_extra_class_enrollments_form",
            ["form"],
            unique=False
        )

        batch_op.create_check_constraint(
            "ck_extra_class_enrollment_form",
            "form IN ('FORM 1', 'FORM 2', 'FORM 3')"
        )


def downgrade():
    with op.batch_alter_table(
        "extra_class_enrollments",
        schema=None
    ) as batch_op:

        batch_op.drop_constraint(
            "ck_extra_class_enrollment_form",
            type_="check"
        )

        batch_op.drop_index(
            "ix_extra_class_enrollments_form"
        )

        batch_op.drop_column("class_name")
        batch_op.drop_column("form")