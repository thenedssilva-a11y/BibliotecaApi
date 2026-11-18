from decimal import Decimal

from flasgger import swag_from
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from flask_pydantic import validate
from sqlalchemy import case, func, or_

from app.extensions import db
from app.models import Livro
from app.schemas import EstoqueInput, LivroInput, LivroPatch
from app.security import admin_required, registrar_auditoria

bp = Blueprint("livros", __name__, url_prefix="/livros")
ERROR_RESPONSES = {"400": {"description": "Requisição inválida"}, "401": {"description": "Autenticação necessária"}, "403": {"description": "Acesso restrito a administrador"}, "404": {"description": "Livro não encontrado"}, "409": {"description": "ISBN duplicado"}, "422": {"description": "Falha de validação"}, "429": {"description": "Limite excedido"}, "500": {"description": "Erro interno"}}


def serialize(book):
    return {"id": book.id, "titulo": book.titulo, "autor": book.autor, "isbn": book.isbn,
            "editora": book.editora, "ano_publicacao": book.ano_publicacao, "categoria": book.categoria,
            "preco": float(book.preco), "quantidade_estoque": book.quantidade_estoque,
            "descricao": book.descricao, "criado_em": book.criado_em.isoformat(),
            "atualizado_em": book.atualizado_em.isoformat()}


def commit_audit(action, book):
    registrar_auditoria(action, "livro", book.id)
    db.session.commit()


@bp.get("")
@swag_from({"tags": ["Livros"], "summary": "Listar livros", "description": "Paginação e busca por título/autor; filtro de categoria e ordenação permitida.", "parameters": [{"name": "page", "in": "query", "type": "integer", "default": 1}, {"name": "per_page", "in": "query", "type": "integer", "default": 20}, {"name": "q", "in": "query", "type": "string"}, {"name": "categoria", "in": "query", "type": "string"}, {"name": "sort", "in": "query", "type": "string", "enum": ["titulo", "autor", "ano_publicacao", "preco", "quantidade_estoque", "criado_em"]}, {"name": "order", "in": "query", "type": "string", "enum": ["asc", "desc"]}], "responses": {"200": {"description": "Página de livros"}, "400": {"description": "Parâmetros inválidos", "schema": {"$ref": "#/definitions/Erro"}}, "401": {"description": "Autenticação necessária", "schema": {"$ref": "#/definitions/Erro"}}, "403": {"description": "Acesso negado", "schema": {"$ref": "#/definitions/Erro"}}, "404": {"description": "Recurso não encontrado", "schema": {"$ref": "#/definitions/Erro"}}, "409": {"description": "Conflito", "schema": {"$ref": "#/definitions/Erro"}}, "422": {"description": "Falha de validação", "schema": {"$ref": "#/definitions/Erro"}}, "429": {"description": "Limite excedido"}, "500": {"description": "Erro interno", "schema": {"$ref": "#/definitions/Erro"}}}})
def list_books():
    try:
        page = max(1, int(request.args.get("page", 1)))
        per_page = min(100, max(1, int(request.args.get("per_page", 20))))
    except ValueError:
        return jsonify(error={"code": "invalid_pagination", "message": "page e per_page devem ser inteiros"}), 400
    query = Livro.query
    term = request.args.get("q", "").strip()
    if term:
        query = query.filter(or_(Livro.titulo.ilike(f"%{term}%"), Livro.autor.ilike(f"%{term}%")))
    category = request.args.get("categoria")
    if category:
        query = query.filter_by(categoria=category)
    # Coluna de ordenação vem de lista fechada, não de SQL fornecido pelo cliente.
    fields = {"titulo": Livro.titulo, "autor": Livro.autor, "ano_publicacao": Livro.ano_publicacao,
              "preco": Livro.preco, "quantidade_estoque": Livro.quantidade_estoque, "criado_em": Livro.criado_em}
    sort = request.args.get("sort", "titulo")
    if sort not in fields:
        return jsonify(error={"code": "invalid_sort", "message": "Campo de ordenação inválido"}), 400
    order = request.args.get("order", "asc").lower()
    if order not in {"asc", "desc"}:
        return jsonify(error={"code": "invalid_order", "message": "order deve ser asc ou desc"}), 400
    query = query.order_by(fields[sort].desc() if order == "desc" else fields[sort].asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    summary = db.session.query(
        func.count(Livro.id),
        func.coalesce(func.sum(Livro.quantidade_estoque), 0),
        func.coalesce(func.sum(case((Livro.quantidade_estoque <= 3, 1), else_=0)), 0),
    ).one()
    categories = [value[0] for value in db.session.query(Livro.categoria).distinct().order_by(Livro.categoria).all()]
    return jsonify(items=[serialize(x) for x in pagination.items], page=page, per_page=per_page,
                   total=pagination.total, pages=pagination.pages,
                   categories=categories,
                   summary={"titles": summary[0], "units": int(summary[1]), "low_stock": int(summary[2])})


@bp.get("/<int:book_id>")
@swag_from({"tags": ["Livros"], "summary": "Obter livro", "description": "Busca um livro pelo identificador numérico.", "parameters": [{"in": "path", "name": "book_id", "type": "integer", "required": True}], "responses": {"200": {"description": "Livro encontrado", "schema": {"$ref": "#/definitions/Livro"}}, **ERROR_RESPONSES}})
def get_book(book_id):
    book = db.session.get(Livro, book_id)
    return (jsonify(serialize(book)), 200) if book else (jsonify(error={"code": "not_found", "message": "Livro não encontrado"}), 404)


@bp.post("")
@jwt_required()
@admin_required
@swag_from({"tags": ["Livros"], "summary": "Cadastrar livro", "description": "Cria um livro. Requer access token de administrador; ISBN precisa ser único.", "security": [{"bearerAuth": []}], "parameters": [{"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/Livro"}}], "responses": {"201": {"description": "Livro criado", "schema": {"$ref": "#/definitions/Livro"}}, **ERROR_RESPONSES}})
@validate()
def create_book(body: LivroInput):
    book = Livro(**body.model_dump())
    db.session.add(book)
    db.session.flush()
    commit_audit("create", book)
    return jsonify(serialize(book)), 201


@bp.put("/<int:book_id>")
@jwt_required()
@admin_required
@swag_from({"tags": ["Livros"], "summary": "Substituir dados do livro", "description": "Substitui todos os campos editáveis. Requer access token de administrador.", "security": [{"bearerAuth": []}], "parameters": [{"in": "path", "name": "book_id", "type": "integer", "required": True}, {"in": "body", "name": "body", "required": True, "schema": {"$ref": "#/definitions/Livro"}}], "responses": {"200": {"description": "Livro atualizado", "schema": {"$ref": "#/definitions/Livro"}}, **ERROR_RESPONSES}})
@validate()
def update_book(body: LivroInput, book_id):
    book = db.session.get(Livro, book_id)
    if not book:
        return jsonify(error={"code": "not_found", "message": "Livro não encontrado"}), 404
    for key, value in body.model_dump().items():
        setattr(book, key, value)
    commit_audit("update", book)
    return jsonify(serialize(book))


@bp.patch("/<int:book_id>/estoque")
@jwt_required()
@admin_required
@swag_from({"tags": ["Estoque"], "summary": "Atualizar quantidade em estoque", "description": "Define a quantidade atual do livro, sem substituir os outros campos.", "security": [{"bearerAuth": []}], "parameters": [{"in": "path", "name": "book_id", "type": "integer", "required": True}, {"in": "body", "name": "body", "required": True, "schema": {"type": "object", "required": ["quantidade_estoque"], "properties": {"quantidade_estoque": {"type": "integer", "minimum": 0}}}}], "responses": {"200": {"description": "Estoque atualizado", "schema": {"$ref": "#/definitions/Livro"}}, **ERROR_RESPONSES}})
@validate()
def update_stock(body: EstoqueInput, book_id):
    book = db.session.get(Livro, book_id)
    if not book:
        return jsonify(error={"code": "not_found", "message": "Livro não encontrado"}), 404
    book.quantidade_estoque = body.quantidade_estoque
    commit_audit("stock_update", book)
    return jsonify(serialize(book))


@bp.delete("/<int:book_id>")
@jwt_required()
@admin_required
@swag_from({"tags": ["Livros"], "summary": "Excluir livro", "description": "Remove definitivamente o livro e registra a ação na auditoria.", "security": [{"bearerAuth": []}], "parameters": [{"in": "path", "name": "book_id", "type": "integer", "required": True}], "responses": {"200": {"description": "Livro excluído"}, **ERROR_RESPONSES}})
def delete_book(book_id):
    book = db.session.get(Livro, book_id)
    if not book:
        return jsonify(error={"code": "not_found", "message": "Livro não encontrado"}), 404
    registrar_auditoria("delete", "livro", book.id)
    db.session.delete(book)
    db.session.commit()
    return jsonify(message="Livro excluído")
