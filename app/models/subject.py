from datetime import datetime

from app import db


class Subject(db.Model):
    __tablename__ = "subjects"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True
    )

    code = db.Column(
        db.String(20),
        nullable=False,
        unique=True
    )

    description = db.Column(
        db.Text,
        nullable=True
    )

    icon = db.Column(
        db.String(20),
        nullable=True
    )

    css_class = db.Column(
        db.String(50),
        nullable=True
    )

    display_order = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    is_practice_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # RELATIONSHIPS (FIXED)
    # ======================================
    
    questions = db.relationship(
    "Question",
    back_populates="subject_ref"
    )

    def __repr__(self):
        return f"<Subject {self.name}>"