import bcrypt
from flask import request
from flask_jwt_extended import get_jwt, get_jwt_identity
from functools import wraps

from app.extensions import db
from app.models import Auditoria, TokenRevogado, Usuario


def hash_senha(senha: str) -> str:
    # Bcrypt com custo 12 torna tentativa offline de senhas mais cara.
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt(rounds=12)).decode()


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(senha.encode(), senha_hash.encode())
    except (ValueError, TypeError):
        return False


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        usuario = db.session.get(Usuario, int(get_jwt_identity()))
        if not usuario or usuario.role != "admin":
            from flask import jsonify
            return jsonify(error={"code": "forbidden", "message": "Acesso restrito a administradores"}), 403
        return fn(*args, **kwargs)
    return wrapper


def registrar_auditoria(acao, entidade, entidade_id=None, usuario_id=None):
    # IP e user-agent são guardados para rastreabilidade do bootstrap e das alterações.
    if usuario_id is None:
        try:
            usuario_id = int(get_jwt_identity())
        except (RuntimeError, TypeError, ValueError):
            usuario_id = None
    registro = Auditoria(usuario_id=usuario_id, acao=acao, entidade=entidade,
                         entidade_id=entidade_id, ip=(request.remote_addr or "")[:45],
                         user_agent=(request.user_agent.string or "")[:500])
    db.session.add(registro)


def is_token_revoked(jwt_header, jwt_payload):
    return db.session.get(TokenRevogado, jwt_payload["jti"]) is not None


def revoke_current_token():
    claims = get_jwt()
    from datetime import datetime, timezone
    expires = datetime.fromtimestamp(claims["exp"], tz=timezone.utc)
    db.session.add(TokenRevogado(jti=claims["jti"], expira_em=expires))
