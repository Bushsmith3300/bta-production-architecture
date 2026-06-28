from flask import Flask
from app.config import Config
from app.extensions import db, migrate, csrf, cors
from app.routes.auth_routes import auth_bp
from app.routes.quiz_routes import quiz_bp
from app.routes.main_routes import main_bp
from app.routes.dashboard_routes import dashboard_bp
from app.routes.announcement_routes import announcement_bp
from app.admin.dashboard_regular_admin import admin_bp
from app.admin.dashboard_super_admin import super_admin_bp
from app.admin.users_management import users_management_bp
from app.admin.admin_management import admin_management_bp 


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
    app.register_blueprint(admin_bp)
    app.register_blueprint(users_management_bp)  
    app.register_blueprint(admin_management_bp) 


    return app