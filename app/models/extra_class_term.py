from datetime import datetime

from dateutil.relativedelta import relativedelta

from app.extensions import db


class ExtraClassTerm(db.Model):
    __tablename__ = "extra_class_terms"

    # ========================================================
    # PRIMARY KEY
    # ========================================================

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    # ========================================================
    # TERM INFORMATION
    # ========================================================

    name = db.Column(
        db.String(150),
        nullable=False
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    # ========================================================
    # TIMESTAMPS
    # ========================================================

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


    # ========================================================
    # RELATIONSHIPS
    # ========================================================

    monthly_fees = db.relationship(
        "ExtraClassMonthlyFee",
        back_populates="term"
    )


    enrollments = db.relationship(
        "ExtraClassEnrollment",
        back_populates="term"
    )


    # ========================================================
    # TABLE CONSTRAINTS
    # ========================================================

    __table_args__ = (
        db.CheckConstraint(
            "end_date >= start_date",
            name="ck_extra_class_term_dates"
        ),
    )

    # ========================================================
    # TERM DURATION
    # ========================================================

    @property
    def duration_display(self):
        """
        Return the term duration using calendar months and days.

        Both the start date and end date are treated as
        inclusive.

        Examples:

            2026-09-01 → 2026-11-30
            = 3 months

            2026-09-10 → 2026-11-24
            = 2 months, 15 days

            2026-09-10 → 2026-09-20
            = 11 days
        """

        if not self.start_date or not self.end_date:
            return "—"

        if self.end_date < self.start_date:
            return "Invalid duration"

        # Add one day because both the start and end dates
        # are included in the term.
        inclusive_end_date = (
            self.end_date + relativedelta(days=1)
        )

        difference = relativedelta(
            inclusive_end_date,
            self.start_date
        )

        parts = []

        # ----------------------------------------------------
        # Years
        # ----------------------------------------------------

        if difference.years:

            parts.append(
                f"{difference.years} "
                f"{'year' if difference.years == 1 else 'years'}"
            )

        # ----------------------------------------------------
        # Months
        # ----------------------------------------------------

        if difference.months:

            parts.append(
                f"{difference.months} "
                f"{'month' if difference.months == 1 else 'months'}"
            )

        # ----------------------------------------------------
        # Days
        # ----------------------------------------------------

        if difference.days:

            parts.append(
                f"{difference.days} "
                f"{'day' if difference.days == 1 else 'days'}"
            )

        # ----------------------------------------------------
        # Fallback
        # ----------------------------------------------------

        return ", ".join(parts) if parts else "1 day"

    # ========================================================
    # REPRESENTATION
    # ========================================================

    def __repr__(self):
        return (
            f"<ExtraClassTerm "
            f"id={self.id} "
            f"name={self.name!r}>"
        )