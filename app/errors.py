from flask import jsonify
from sqlalchemy.exc import IntegrityError
from werkzeug.exceptions import HTTPException

from app.extensions import db


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {400: "Requisição inválida", 401: "Autenticação necessária", 403: "Acesso negado",
                    404: "Recurso não encontrado", 413: "Corpo da requisição excede 100 KB",
                    429: "Limite de requisições excedido"}
        return jsonify(error={"code": error.name.lower().replace(" ", "_"),
                              "message": messages.get(error.code, "Não foi possível processar a requisição")}), error.code

    @app.errorhandler(IntegrityError)
    def integrity_error(_error):
        db.session.rollback()
        return jsonify(error={"code": "conflict", "message": "Registro duplicado ou inconsistente"}), 409

    @app.errorhandler(Exception)
    def unexpected_error(_error):
        db.session.rollback()
        app.logger.exception("Erro interno não exposto ao cliente")
        return jsonify(error={"code": "internal_error", "message": "Erro interno do servidor"}), 500

