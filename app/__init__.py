from flask import Flask
from app.config import Config
from app.extensions import db, migrate, csrf, cors
from app.routes.auth_routes import auth_bp
from app.routes.quiz_routes import quiz_bp
from app.routes.main_routes import main_bp
from app.routes.dashboard_routes import dashboard_bp
from app.routes.announcement_routes import announcement_bp
from app.admin.dashboard_regular_admin import regular_admin_bp
from app.admin.dashboard_super_admin import super_admin_bp
from app.admin.users_management import users_management_bp
from app.admin.admin_management import admin_management_bp 
from app.admin.questions_management import questions_bp
from app.admin.extra_class_management import extra_class_bp
from app.routes.extra_class_auth import extra_class_auth_bp
from app.routes.extra_class_teacher import extra_class_teacher_bp
from app.routes.extra_class_payment import extra_class_payment_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    cors.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(announcement_bp)
    app.register_blueprint(super_admin_bp)
    app.register_blueprint(regular_admin_bp)
    app.register_blueprint(users_management_bp)  
    app.register_blueprint(admin_management_bp) 
    app.register_blueprint(questions_bp)
    app.register_blueprint(extra_class_bp)
    app.register_blueprint(extra_class_auth_bp)
    app.register_blueprint(extra_class_teacher_bp)
    app.register_blueprint(extra_class_payment_bp)


    return app