# Referência da API

Base URL local: `http://127.0.0.1:5000`. A interface Swagger em `/apidocs` é a referência interativa; o documento gerado fica em `/apispec_1.json`.

## Fluxo de autenticação

1. `POST /setup/admin` cria o primeiro administrador apenas uma vez.
2. `POST /auth/login` devolve `access_token`; use `Authorization: Bearer <token>` nas rotas protegidas. O refresh é cookie HttpOnly.
3. `POST /auth/refresh` renova o access token usando o cookie; `POST /auth/logout` revoga o refresh atual.
4. Leitura de livros é pública; criação, alteração, atualização de estoque e exclusão exigem administrador.

## Livros

`GET /livros?page=1&per_page=20&q=termo&categoria=Romance&sort=titulo&order=asc` retorna `{items, page, per_page, total, pages}`. `q` pesquisa título e autor. A ordenação aceita `titulo`, `autor`, `ano_publicacao`, `preco`, `quantidade_estoque` ou `criado_em`; `per_page` tem máximo de 100.

`POST /livros` e `PUT /livros/{id}` recebem `titulo`, `autor`, `isbn`, `editora`, `ano_publicacao`, `categoria`, `preco`, `quantidade_estoque` e `descricao`. ISBN duplicado resulta em `409`; IDs inexistentes em `404`; corpo inválido em `422`. `PATCH /livros/{id}/estoque` recebe `{ "quantidade_estoque": 5 }`.

## Formato de erro

```json
{"error":{"code":"not_found","message":"Livro não encontrado"}}
```

Erros de validação também incluem `details` com os campos que falharam, sem copiar valores de senha ou o corpo enviado. `401` indica ausência/invalidade de autenticação; `403` indica papel insuficiente ou setup já concluído; `429` indica limite excedido; `500` não revela exceções, SQL ou stack trace.
