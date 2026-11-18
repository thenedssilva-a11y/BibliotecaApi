swagger_template = {
    "swagger": "2.0",
    "info": {"title": "API de Gestão de Estoque de Livros", "description": "API REST para cadastro e controle de estoque.", "version": "1.0.0"},
    "basePath": "/",
    "schemes": ["http", "https"],
    "securityDefinitions": {"bearerAuth": {"type": "apiKey", "name": "Authorization", "in": "header", "description": "Cole o access_token retornado pelo login. Pode colar com ou sem o prefixo Bearer."}},
    "definitions": {
        "Erro": {"type": "object", "properties": {"error": {"type": "object", "properties": {"code": {"type": "string"}, "message": {"type": "string"}}}}},
        "Livro": {"type": "object", "required": ["titulo", "autor", "isbn", "editora", "ano_publicacao", "categoria", "preco", "quantidade_estoque"], "properties": {"id": {"type": "integer", "readOnly": True}, "titulo": {"type": "string", "maxLength": 200}, "autor": {"type": "string", "maxLength": 160}, "isbn": {"type": "string", "minLength": 10, "maxLength": 17}, "editora": {"type": "string", "maxLength": 160}, "ano_publicacao": {"type": "integer", "minimum": 0}, "categoria": {"type": "string", "maxLength": 80}, "preco": {"type": "number", "minimum": 0}, "quantidade_estoque": {"type": "integer", "minimum": 0}, "descricao": {"type": "string", "maxLength": 2000}, "criado_em": {"type": "string", "format": "date-time", "readOnly": True}, "atualizado_em": {"type": "string", "format": "date-time", "readOnly": True}}},
    },
}
