from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class Livro(db.Model):
    __tablename__ = "livros"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False, index=True)
    autor = db.Column(db.String(160), nullable=False, index=True)
    isbn = db.Column(db.String(17), unique=True, nullable=False, index=True)
    editora = db.Column(db.String(160), nullable=False)
    ano_publicacao = db.Column(db.Integer, nullable=False)
    categoria = db.Column(db.String(80), nullable=False, index=True)
    preco = db.Column(db.Numeric(10, 2), nullable=False)
    quantidade_estoque = db.Column(db.Integer, nullable=False, default=0)
    descricao = db.Column(db.String(2000), nullable=False, default="")
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    atualizado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class Auditoria(db.Model):
    __tablename__ = "auditoria"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    acao = db.Column(db.String(40), nullable=False)
    entidade = db.Column(db.String(40), nullable=False)
    entidade_id = db.Column(db.Integer, nullable=True)
    ip = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.String(500), nullable=False, default="")
    criado_em = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class TokenRevogado(db.Model):
    __tablename__ = "tokens_revogados"
    jti = db.Column(db.String(36), primary_key=True)
    expira_em = db.Column(db.DateTime(timezone=True), nullable=False)


class SetupGuard(db.Model):
    # PK fixa coordena chamadas simultâneas do bootstrap sem SQL escrito à mão.
    __tablename__ = "setup_guard"
    id = db.Column(db.Integer, primary_key=True)
