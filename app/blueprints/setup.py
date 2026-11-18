from flasgger import swag_from
from flask import Blueprint, jsonify, request
from flask_pydantic import validate

from app.extensions import db
from sqlalchemy.exc import IntegrityError

from app.models import SetupGuard, Usuario
from app.schemas import AdminSetup
from app.security import hash_senha, registrar_auditoria

bp = Blueprint("setup", __name__, url_prefix="/setup")

SETUP_DOC = {
    "tags": ["Setup"], "summary": "Criar primeiro administrador",
    "description": "Cria o primeiro administrador somente enquanto a tabela de usuários estiver vazia. Requer senha forte.",
    "security": [],
    "parameters": [{"in": "body", "name": "body", "required": True, "schema": {"type": "object", "required": ["nome", "email", "senha"], "properties": {"nome": {"type": "string", "example": "Admin"}, "email": {"type": "string", "example": "admin@exemplo.com"}, "senha": {"type": "string", "example": "SenhaForte#2026"}}}}],
    "responses": {"201": {"description": "Administrador criado"}, "400": {"description": "Payload inválido", "schema": {"$ref": "#/definitions/Erro"}}, "401": {"description": "Autenticação necessária", "schema": {"$ref": "#/definitions/Erro"}}, "403": {"description": "Setup já concluído", "schema": {"$ref": "#/definitions/Erro"}}, "404": {"description": "Recurso não encontrado", "schema": {"$ref": "#/definitions/Erro"}}, "409": {"description": "Conflito", "schema": {"$ref": "#/definitions/Erro"}}, "422": {"description": "Falha de validação", "schema": {"$ref": "#/definitions/Erro"}}, "429": {"description": "Limite excedido"}, "500": {"description": "Erro interno", "schema": {"$ref": "#/definitions/Erro"}}}
}


@bp.post("/admin")
@swag_from(SETUP_DOC)
@validate()
def create_admin(body: AdminSetup):
    # PK fixa serializa o bootstrap e impede duas primeiras contas concorrentes.
    try:
        db.session.add(SetupGuard(id=1))
        db.session.flush()
    except IntegrityError:
        db.session.rollback()
        return jsonify(error={"code": "setup_complete", "message": "O administrador inicial já foi criado"}), 403
    # Checagem e INSERT ficam na mesma transação; e-mail também tem restrição unique.
    if db.session.query(Usuario.id).first() is not None:
        db.session.rollback()
        return jsonify(error={"code": "setup_complete", "message": "O administrador inicial já foi criado"}), 403
    usuario = Usuario(nome=body.nome, email=str(body.email).lower(), senha_hash=hash_senha(body.senha), role="admin")
    db.session.add(usuario)
    db.session.flush()
    registrar_auditoria("create", "usuario", usuario.id, usuario.id)
    db.session.commit()
    return jsonify(id=usuario.id, nome=usuario.nome, email=usuario.email, role=usuario.role), 201
