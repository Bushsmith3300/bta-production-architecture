"""add hash column to question model

Revision ID: 75ca0410dc39
Revises: 01c37d94af30
Create Date: 2026-07-12 19:08:03.892624

"""

from alembic import op
import sqlalchemy as sa
import hashlib


# revision identifiers, used by Alembic.
revision = "75ca0410dc39"
down_revision = "01c37d94af30"
branch_labels = None
depends_on = None



def generate_hash(text):

    normalized = text.strip().lower()

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()



def upgrade():

    # Step 1:
    # Add column temporarily allowing NULL
    with op.batch_alter_table(
        "question",
        schema=None
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "question_hash",
                sa.String(length=64),
                nullable=True
            )
        )


    # Step 2:
    # Populate hashes for existing questions

    connection = op.get_bind()


    questions = connection.execute(
        sa.text(
            """
            SELECT id, question_text
            FROM question
            """
        )
    )


    for question in questions:

        question_id = question.id

        question_text = question.question_text


        hash_value = generate_hash(
            question_text
        )


        connection.execute(
            sa.text(
                """
                UPDATE question
                SET question_hash = :hash
                WHERE id = :id
                """
            ),
            {
                "hash": hash_value,
                "id": question_id
            }
        )


    # Step 3:
    # Make column required and indexed

    with op.batch_alter_table(
        "question",
        schema=None
    ) as batch_op:


        batch_op.alter_column(
            "question_hash",
            nullable=False
        )


        batch_op.create_index(
            "ix_question_question_hash",
            [
                "question_hash"
            ],
            unique=False
        )



def downgrade():

    with op.batch_alter_table(
        "question",
        schema=None
    ) as batch_op:


        batch_op.drop_index(
            "ix_question_question_hash"
        )


        batch_op.drop_column(
            "question_hash"
        )