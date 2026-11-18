from datetime import datetime, timezone

from flasgger import swag_from
from flask import Blueprint, jsonify, make_response
from flask_jwt_extended import (create_access_token, create_refresh_token, get_jwt,
                                get_jwt_identity, jwt_required, set_refresh_cookies,
                                unset_jwt_cookies)
from flask_pydantic import validate

from app.extensions import db, limiter
from app.models import TokenRevogado, Usuario
from app.schemas import LoginInput
from app.security import revoke_current_token, verificar_senha

bp = Blueprint("auth", __name__, url_prefix="/auth")
ERROR_RESPONSES = {"400": {"description": "Requisição inválida"}, "401": {"description": "Credenciais ou token inválidos"}, "403": {"description": "Acesso negado"}, "404": {"description": "Recurso não encontrado"}, "409": {"description": "Conflito"}, "422": {"description": "Falha de validação"}, "429": {"description": "Limite excedido"}, "500": {"description": "Erro interno"}}


@bp.post("/login")
@limiter.limit("5 per 5 minutes")
@swag_from({"tags": ["Auth"], "summary": "Autenticar usuário", "description": "Retorna access JWT de 15 minutos; refresh JWT é enviado em cookie HttpOnly.", "security": [], "parameters": [{"in": "body", "name": "body", "required": True, "schema": {"type": "object", "required": ["email", "senha"], "properties": {"email": {"type": "string"}, "senha": {"type": "string"}}}}], "responses": {"200": {"description": "Login efetuado"}, **ERROR_RESPONSES}})
@validate()
def login(body: LoginInput):
    usuario = Usuario.query.filter_by(email=str(body.email).lower()).first()
    if not usuario or not verificar_senha(body.senha, usuario.senha_hash):
        return jsonify(error={"code": "invalid_credentials", "message": "E-mail ou senha inválidos"}), 401
    access = create_access_token(identity=str(usuario.id), additional_claims={"role": usuario.role})
    refresh = create_refresh_token(identity=str(usuario.id), additional_claims={"role": usuario.role})
    response = make_response(jsonify(access_token=access, token_type="Bearer", expires_in=900,
                                     usuario={"id": usuario.id, "nome": usuario.nome, "email": usuario.email, "role": usuario.role}))
    # Refresh não fica acessível ao JavaScript; SameSite Strict reduz CSRF.
    set_refresh_cookies(response, refresh, max_age=30 * 24 * 60 * 60)
    return response


@bp.post("/refresh")
@jwt_required(refresh=True, locations=["cookies"])
@swag_from({"tags": ["Auth"], "summary": "Renovar access token", "description": "Lê o refresh cookie HttpOnly e devolve um novo access token. Requer o valor csrf_refresh_token no cabeçalho X-CSRF-TOKEN.", "security": [], "responses": {"200": {"description": "Token renovado"}, **ERROR_RESPONSES}})
def refresh():
    usuario = db.session.get(Usuario, int(get_jwt_identity()))
    if not usuario:
        return jsonify(error={"code": "invalid_token", "message": "Token inválido"}), 401
    token = create_access_token(identity=str(usuario.id), additional_claims={"role": usuario.role})
    return jsonify(access_token=token, token_type="Bearer", expires_in=900)


@bp.post("/logout")
@jwt_required(refresh=True, locations=["cookies"])
@swag_from({"tags": ["Auth"], "summary": "Encerrar sessão", "description": "Revoga o refresh token atual e remove os cookies. Requer o valor csrf_refresh_token no cabeçalho X-CSRF-TOKEN.", "security": [], "responses": {"200": {"description": "Logout efetuado"}, **ERROR_RESPONSES}})
def logout():
    claims = get_jwt()
    db.session.add(TokenRevogado(jti=claims["jti"], expira_em=datetime.fromtimestamp(claims["exp"], tz=timezone.utc)))
    db.session.commit()
    response = make_response(jsonify(message="Logout efetuado"))
    unset_jwt_cookies(response)
    return response


@bp.get("/me")
@jwt_required()
@swag_from({"tags": ["Auth"], "summary": "Consultar usuário autenticado", "security": [{"bearerAuth": []}], "responses": {"200": {"description": "Usuário autenticado"}, **ERROR_RESPONSES}})
def me():
    usuario = db.session.get(Usuario, int(get_jwt_identity()))
    if not usuario:
        return jsonify(error={"code": "invalid_token", "message": "Usuário do token não existe"}), 401
    return jsonify(id=usuario.id, nome=usuario.nome, email=usuario.email, role=usuario.role)
