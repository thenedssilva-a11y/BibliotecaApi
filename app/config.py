import os
import secrets
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(48)
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(48)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///livros.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"
    JWT_REFRESH_COOKIE_NAME = "refresh_token_cookie"
    JWT_COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0") == "1"
    COOKIE_SECURE = JWT_COOKIE_SECURE
    JWT_COOKIE_SAMESITE = "Strict"
    JWT_COOKIE_CSRF_IN_COOKIES = True
    JWT_COOKIE_CSRF_CSRF_HEADER_NAME = "X-CSRF-TOKEN"
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5000")
    AUTO_MIGRATE = os.getenv("AUTO_MIGRATE", "1") == "1"
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    # Requisições recebem um limite padrão; login define limite mais estrito no blueprint.
    RATELIMIT_DEFAULT = "100 per 15 minutes"
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    FLASK_PYDANTIC_VALIDATION_ERROR_STATUS_CODE = 422
    FLASK_PYDANTIC_VALIDATION_ERROR_RAISE = True
    # auth precisa ser JSON válido: Flasgger injeta esse valor diretamente no JavaScript da UI.
    SWAGGER = {"title": "API de Gestão de Estoque de Livros", "uiversion": 3, "auth": "{}"}

