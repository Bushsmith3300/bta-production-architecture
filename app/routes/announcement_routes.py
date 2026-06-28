# app/routes/announcement_routes.py

from flask import (
    Blueprint,
    render_template,
    session
)

from app.models import (
    User,
    Announcement,
    Quote
)

from app.utils.decorators import login_required


announcement_bp = Blueprint(
    "announcement",
    __name__
)


# ---------------- ANNOUNCEMENTS ----------------
@announcement_bp.route("/announcements")
@login_required

def announcement_page():

    user = User.query.get(
        session["user_id"]
    )

    announcements = Announcement.query.all()

    quote = Quote.query.first()

    return render_template(
        "announcements.html",
        announcements=announcements,
        user=user,
        today_quote=quote
    )