import pytest
from datetime import timedelta

from app import create_app
from app.extensions import db


class TestConfig:
    TESTING = True
    DEBUG = True
    SECRET_KEY = "test-secret-key-that-is-at-least-32-bytes"
    JWT_SECRET_KEY = "test-jwt-secret-key-that-is-at-least-32-bytes"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    AUTO_MIGRATE = False
    FRONTEND_ORIGIN = "http://localhost"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_CSRF_PROTECT = False
    COOKIE_SECURE = False
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = "Strict"
    RATELIMIT_ENABLED = False
    SWAGGER = {"title": "API de Teste", "uiversion": 3, "auth": "{}"}
    FLASK_PYDANTIC_VALIDATION_ERROR_STATUS_CODE = 422
    FLASK_PYDANTIC_VALIDATION_ERROR_RAISE = True


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_token(client):
    client.post("/setup/admin", json={"nome": "Admin", "email": "admin@example.com", "senha": "SenhaForte#2026"})
    response = client.post("/auth/login", json={"email": "admin@example.com", "senha": "SenhaForte#2026"})
    return response.json["access_token"]
