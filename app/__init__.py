from pathlib import Path
import os

from flasgger import Swagger
from flask import Flask, render_template, request
from flask_pydantic.exceptions import JsonBodyParsingError, ValidationError as PydanticRequestError
from flask_migrate import upgrade

from app.config import Config
from app.errors import register_error_handlers
from app.extensions import cors, db, jwt, limiter, migrate, talisman
from app.swagger.template import swagger_template


def create_app(config_object=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    if config_object is Config and not app.config["DEBUG"] and (not os.getenv("SECRET_KEY") or not os.getenv("JWT_SECRET_KEY")):
        raise RuntimeError("Configure SECRET_KEY e JWT_SECRET_KEY no ambiente antes de iniciar em produção.")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    @app.before_request
    def normalize_swagger_bearer_header():
        # Swagger 2 apiKey auth envia literalmente o valor digitado. Aceite o
        # JWT puro colado no campo e normalize para o formato esperado pelo JWT.
        authorization = request.headers.get("Authorization", "").strip()
        if authorization and not authorization.lower().startswith("bearer ") and authorization.count(".") == 2:
            request.environ["HTTP_AUTHORIZATION"] = f"Bearer {authorization}"


    # Limite global do corpo reduz abuso de memória e rejeita uploads desnecessários.
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024
    db.init_app(app)
    migrate.init_app(app, db, directory=str(Path(app.root_path).parent / "migrations"))
    jwt.init_app(app)
    limiter.init_app(app)
    talisman.init_app(
        app,
        force_https=app.config["COOKIE_SECURE"],
        frame_options="DENY",
        content_security_policy={
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'"],
            "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
            "img-src": ["'self'", "data:"],
            "object-src": ["'none'"],
            "frame-ancestors": ["'none'"],
        },
        strict_transport_security=app.config["COOKIE_SECURE"],
        strict_transport_security_max_age=31536000,
        referrer_policy="no-referrer",
    )
    # CORS usa uma origem configurada, nunca curingas com credenciais.
    cors.init_app(
        app,
        resources={r"/*": {"origins": app.config["FRONTEND_ORIGIN"]}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "X-CSRF-TOKEN"],
    )
    Swagger(app, template=swagger_template, config={
        "headers": [],
        "specs": [{"endpoint": "apispec_1", "route": "/apispec_1.json",
                   "rule_filter": lambda _rule: True, "model_filter": lambda _tag: True}],
        "specs_route": "/apidocs/",
        "static_url_path": "/flasgger_static",
    })
    register_error_handlers(app)

    @app.errorhandler(PydanticRequestError)
    def pydantic_request_error(error):
        from flask import jsonify
        raw = {"body_params": error.body_params, "form_params": error.form_params,
               "path_params": error.path_params, "query_params": error.query_params}
        def safe_details(value):
            if isinstance(value, dict):
                return {key: safe_details(item) for key, item in value.items() if key not in {"input", "ctx"}}
            if isinstance(value, list):
                return [safe_details(item) for item in value]
            if isinstance(value, (str, int, float, bool)) or value is None:
                return value
            return str(value)
        return jsonify(error={"code": "validation_error", "message": "Falha de validação", "details": safe_details(raw)}), 422

    @app.errorhandler(JsonBodyParsingError)
    def malformed_json(_error):
        from flask import jsonify
        return jsonify(error={"code": "invalid_json", "message": "Corpo JSON inválido"}), 400

    @app.after_request
    def normalize_validation_error(response):
        # Pydantic details are returned without echoing the submitted field values.
        if response.status_code == 422 and response.is_json:
            payload = response.get_json(silent=True) or {}
            if "validation_error" in payload:
                from flask import jsonify
                def safe_details(value):
                    if isinstance(value, dict):
                        return {key: safe_details(item) for key, item in value.items() if key not in {"input", "ctx"}}
                    if isinstance(value, list):
                        return [safe_details(item) for item in value]
                    return value
                return jsonify(error={"code": "validation_error", "message": "Falha de validação", "details": safe_details(payload["validation_error"])}), 422
        return response

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.livros import bp as livros_bp
    from app.blueprints.setup import bp as setup_bp
    from app.models import TokenRevogado  # noqa: F401 - registers models before migrations.
    from app.cli import create_admin_command

    app.register_blueprint(setup_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(livros_bp)
    app.cli.add_command(create_admin_command)

    @app.get("/")
    def index():
        return render_template("index.html")

    @jwt.token_in_blocklist_loader
    def check_revoked(_header, payload):
        return db.session.get(TokenRevogado, payload["jti"]) is not None

    @jwt.unauthorized_loader
    def missing_token(_reason):
        from flask import jsonify
        return jsonify(error={"code": "authentication_required", "message": "Autenticação necessária"}), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        from flask import jsonify
        return jsonify(error={"code": "invalid_token", "message": "Token inválido"}), 401

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        from flask import jsonify
        return jsonify(error={"code": "expired_token", "message": "Token expirado"}), 401

    @jwt.revoked_token_loader
    def revoked_token(_header, _payload):
        from flask import jsonify
        return jsonify(error={"code": "revoked_token", "message": "Token revogado"}), 401

    @app.get("/apidocs")
    def docs_redirect():
        # Flasgger monta a interface em /apidocs/.
        from flask import redirect
        return redirect("/apidocs/")

    # Em desenvolvimento, aplicar as migrations automaticamente permite `flask run`
    # em uma instalação nova; produção deve promover migrations no deploy.
    if app.config["AUTO_MIGRATE"]:
        with app.app_context():
            upgrade(directory=str(Path(app.root_path).parent / "migrations"))

    return app
