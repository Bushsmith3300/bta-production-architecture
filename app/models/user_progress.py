from app.extensions import db
from datetime import datetime


class UserProgress(db.Model):

    __tablename__ = "user_progress"

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "subject",
            name="unique_user_subject"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    subject = db.Column(
        db.String(30),
        nullable=True,
        index=True
    )

    questions_attempted = db.Column(
        db.Integer,
        default=0
    )

    correct_answers = db.Column(
        db.Integer,
        default=0
    )


    last_attempt = db.Column(
        db.DateTime
    )

    #------- Relationship back to User-------


    user = db.relationship(
        "User",
        back_populates="user_progress"
    )