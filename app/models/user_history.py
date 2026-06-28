from app.extensions import db
from datetime import datetime



class UserHistory(db.Model):

    __tablename__ = "user_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "question.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )

 
    selected_answer = db.Column(
        db.String(1),
        nullable=False
    )

    is_correct = db.Column(
        db.Boolean,
        nullable=False
    )

    attempted_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )


#-------RELATIONSHIPS--------

    user = db.relationship(
        "User",
        back_populates="user_history"
    )

    question = db.relationship(
        "Question",
        back_populates="user_history"
    )