# app/models/quote.py

from app.extensions import db


class Quote(db.Model):

    __tablename__ = "today_quote"

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
        db.String(500),
        nullable=True
    )

    message = db.Column(
        db.Text,
        nullable=True
    )

    action = db.Column(
        db.String(500),
        nullable=True
    )

    #----- relationship back to User/Admin------

    admin = db.relationship(
        "User",
        back_populates="quotes_created"
    )

    def __repr__(self):
        return f"<Quote {self.id}>"