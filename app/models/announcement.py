from app.extensions import db
from datetime import datetime


class Announcement(db.Model):

    __tablename__ = "announcements"


    id = db.Column(
        db.Integer,
        primary_key=True
    )


    admin_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )


    title = db.Column(
        db.String(150),
        nullable=False
    )


    message = db.Column(
        db.Text,
        nullable=False
    )


    scheduled_date = db.Column(
        db.String(150),
        nullable=True
    )


    scheduled_time = db.Column(
        db.String(150),
        nullable=True
    )


    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )


    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    subject = db.Column(
        db.String(30),
        nullable=True,
        index=True
    )


    audience = db.Column(
        db.String(20),
         default="student",
        nullable=False,
        index=True
    )


    # =========================
    # RELATIONSHIPS
    # =========================

    admin = db.relationship(
        "User",
        back_populates="announcements_created"
    )

    def __repr__(self):
        return f"<Announcement {self.title}>"