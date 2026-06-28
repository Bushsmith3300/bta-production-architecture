# app/config.py

import os

from dotenv import load_dotenv

from datetime import timedelta

from sqlalchemy.pool import NullPool

load_dotenv()


class Config:

    SECRET_KEY = os.getenv("SECRET_KEY")

    SESSION_PERMANENT = True

    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=30
    )

    PREFERRED_URL_SCHEME = (
        "https"
        if os.getenv("RENDER_ENV") == "production"
        else "http"
    )

    SESSION_COOKIE_HTTPONLY = True

    SESSION_COOKIE_SAMESITE = "Lax"

    SESSION_COOKIE_SECURE = (
        os.getenv("RENDER_ENV") == "production"
    )

    SESSION_COOKIE_NAME = (
        "__Host-session"
        if os.getenv("RENDER_ENV") == "production"
        else "session"
    )

    # DATABASE
    database_url = os.getenv("DATABASE_URL")

    if not database_url:

        if os.getenv("RENDER_ENV") == "production":

            raise ValueError(
                "DATABASE_URL must be set"
            )

        database_url = "sqlite:///chemistry.db"

    if database_url.startswith("postgres://"):

        database_url = database_url.replace(
            "postgres://",
            "postgresql://",
            1
        )

    SQLALCHEMY_DATABASE_URI = database_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    if database_url.startswith("postgresql://"):

       SQLALCHEMY_ENGINE_OPTIONS = {

        # --- Connection robustness ---

       "pool_pre_ping": True,        # checks dead connections before using them
       "pool_recycle": 1800,         # recycle connections every 30 min
       "pool_timeout": 30,           # wait time before failing to get connection

       # --- Pool sizing (important for Supabase + small apps) ---

      "pool_size": 5,               # number of persistent connections
      "max_overflow": 10,          # extra temporary connections

      # --- Stability improvement ---

      "connect_args": {
        "sslmode": "require",
        "connect_timeout": 10     # prevents infinite hanging on bad networks
    }
}
