from flask import Blueprint

admin_bp = Blueprint(
    "admin",
    __name__)

from app.admin import dashboard_super_admin
from app.admin import users_management
from app.admin import dashboard_regular_admin
from app.admin import questions
from app.admin import exercises 