"""Add columns to Question table

Revision ID: 01c37d94af30
Revises: 622c64c854c0
Create Date: 2026-07-12 16:35:46.259961

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "01c37d94af30"
down_revision = "622c64c854c0"
branch_labels = None
depends_on = None


difficulty_enum = sa.Enum(
    "DOK_1",
    "DOK_2",
    "DOK_3",
    "DOK_4",
    name="difficulty_level"
)


def upgrade():

    bind = op.get_bind()

    # Create PostgreSQL ENUM type first
    difficulty_enum.create(bind, checkfirst=True)

    with op.batch_alter_table("question", schema=None) as batch_op:

        batch_op.add_column(
            sa.Column(
                "subject",
                sa.String(length=50),
                nullable=False,
                server_default="Chemistry"
            )
        )

        batch_op.add_column(
            sa.Column(
                "difficulty",
                difficulty_enum,
                nullable=False,
                server_default="DOK_1"
            )
        )

        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now()
            )
        )

        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now()
            )
        )

        batch_op.alter_column(
            "question_text",
            existing_type=sa.VARCHAR(length=500),
            type_=sa.Text(),
            existing_nullable=False
        )

        batch_op.alter_column(
            "explanation",
            existing_type=sa.VARCHAR(length=1000),
            type_=sa.Text(),
            existing_nullable=True
        )

    # Remove temporary server defaults
    with op.batch_alter_table("question", schema=None) as batch_op:

        batch_op.alter_column(
            "subject",
            server_default=None
        )

        batch_op.alter_column(
            "difficulty",
            server_default=None
        )

        batch_op.alter_column(
            "created_at",
            server_default=None
        )

        batch_op.alter_column(
            "updated_at",
            server_default=None
        )


def downgrade():

    with op.batch_alter_table("question", schema=None) as batch_op:

        batch_op.alter_column(
            "explanation",
            existing_type=sa.Text(),
            type_=sa.VARCHAR(length=1000),
            existing_nullable=True
        )

        batch_op.alter_column(
            "question_text",
            existing_type=sa.Text(),
            type_=sa.VARCHAR(length=500),
            existing_nullable=False
        )

        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("difficulty")
        batch_op.drop_column("subject")

    bind = op.get_bind()

    # Drop ENUM type
    difficulty_enum.drop(bind, checkfirst=True)