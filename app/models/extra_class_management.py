from flask import Blueprint, render_template

from app.utils.decorators import admin_required


extra_class_bp = Blueprint(
    "extra_class",
    __name__,
    url_prefix="/admin/extra-classes"
)


@extra_class_bp.route("/")
@admin_required
def dashboard():
    return render_template(
        "admin/extra_classes/dashboard.html"
    )