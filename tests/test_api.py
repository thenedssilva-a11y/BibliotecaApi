from app.extensions import db
from app.models import Auditoria, Usuario
from app.security import hash_senha


def admin_headers(token):
    return {"Authorization": f"Bearer {token}"}


def valid_book(**overrides):
    data = {"titulo": "O Guia", "autor": "A. Autora", "isbn": "9781234567890", "editora": "Editora X",
            "ano_publicacao": 2020, "categoria": "Fantasia", "preco": 45.90, "quantidade_estoque": 8, "descricao": "Livro"}
    data.update(overrides)
    return data


def test_setup_bootstrap_is_single_use_and_audited(client, app):
    body = {"nome": "Admin", "email": "ADMIN@example.com", "senha": "SenhaForte#2026"}
    first = client.post("/setup/admin", json=body)
    second = client.post("/setup/admin", json=body)
    assert first.status_code == 201
    assert second.status_code == 403
    with app.app_context():
        assert Usuario.query.count() == 1
        assert Auditoria.query.filter_by(acao="create", entidade="usuario").count() == 1


def test_setup_rejects_weak_password(client):
    response = client.post("/setup/admin", json={"nome": "Admin", "email": "a@example.com", "senha": "weak"})
    assert response.status_code in (400, 422)


def test_login_and_write_authorization(client, app, admin_token):
    response = client.post("/livros", json=valid_book())
    assert response.status_code == 401
    with app.app_context():
        db.session.add(Usuario(nome="Leitor", email="user@example.com", senha_hash=hash_senha("SenhaForte#2026"), role="user"))
        db.session.commit()
    login = client.post("/auth/login", json={"email": "user@example.com", "senha": "SenhaForte#2026"})
    forbidden = client.post("/livros", headers=admin_headers(login.json["access_token"]), json=valid_book())
    assert login.status_code == 200
    assert forbidden.status_code == 403
    assert any(key[2] == "refresh_token_cookie" for key in client._cookies)


def test_books_crud_search_conflict_and_stock(client, admin_token):
    headers = admin_headers(admin_token)
    created = client.post("/livros", headers=headers, json=valid_book())
    assert created.status_code == 201
    book_id = created.json["id"]
    assert client.post("/livros", headers=headers, json=valid_book()).status_code == 409
    assert client.get("/livros?q=Guia&categoria=Fantasia").json["total"] == 1
    assert client.get(f"/livros/{book_id}").status_code == 200
    stock = client.patch(f"/livros/{book_id}/estoque", headers=headers, json={"quantidade_estoque": 3})
    assert stock.status_code == 200 and stock.json["quantidade_estoque"] == 3
    updated = client.put(f"/livros/{book_id}", headers=headers, json=valid_book(titulo="Novo título"))
    assert updated.status_code == 200 and updated.json["titulo"] == "Novo título"
    assert client.delete(f"/livros/{book_id}", headers=headers).status_code == 200
    assert client.get(f"/livros/{book_id}").status_code == 404


def test_validation_and_docs(client, admin_token):
    invalid = client.post("/livros", headers=admin_headers(admin_token), json=valid_book(preco=-1))
    assert invalid.status_code in (400, 422)
    assert client.get("/apidocs/").status_code == 200
    spec = client.get("/apispec_1.json")
    assert spec.status_code == 200
    assert "bearerAuth" in spec.json.get("securityDefinitions", {})
    assert "/setup/admin" in spec.json["paths"]
    assert spec.json["paths"]["/setup/admin"]["post"].get("security") == []


def test_invalid_payload_is_422_without_echoing_password(client):
    secret = "this-is-the-submitted-password"
    response = client.post("/setup/admin", json={"nome": "A", "email": "not-an-email", "senha": secret})
    assert response.status_code == 422
    assert response.json["error"]["code"] == "validation_error"
    assert secret not in response.get_data(as_text=True)


def test_refresh_cookie_is_httponly_samesite_and_csrf_protected(client, app):
    app.config["JWT_COOKIE_CSRF_PROTECT"] = True
    client.post("/setup/admin", json={"nome": "Admin", "email": "csrf@example.com", "senha": "SenhaForte#2026"})
    response = client.post("/auth/login", json={"email": "csrf@example.com", "senha": "SenhaForte#2026"})
    assert response.status_code == 200
    cookie = next(value for key, value in client._cookies.items() if key[2] == "refresh_token_cookie")
    assert cookie.http_only is True
    assert cookie.same_site == "Strict"
    assert client.post("/auth/refresh").status_code == 401
    csrf = next(value.value for key, value in client._cookies.items() if key[2] == "csrf_refresh_token")
    assert client.post("/auth/refresh", headers={"X-CSRF-TOKEN": csrf}).status_code == 200


def test_home_security_headers_and_explicit_cors_origin(client):
    allowed = client.get("/", headers={"Origin": "http://localhost"})
    assert allowed.status_code == 200
    assert b"Seu cat\xc3\xa1logo" in allowed.data
    assert allowed.headers["X-Content-Type-Options"] == "nosniff"
    assert allowed.headers["X-Frame-Options"] == "DENY"
    assert allowed.headers["Referrer-Policy"] == "no-referrer"
    assert "'unsafe-inline'" in allowed.headers["Content-Security-Policy"]
    assert "nonce-" not in allowed.headers["Content-Security-Policy"]
    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost"
    denied = client.get("/", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in denied.headers


def test_swagger_ui_assets_are_available_and_template_has_valid_auth_config(client):
    html = client.get("/apidocs/")
    assert html.status_code == 200
    source = html.get_data(as_text=True)
    assert "/flasgger_static/swagger-ui.css" in source
    assert "let auth_config = {};" in source
    assert client.get("/flasgger_static/swagger-ui.css").status_code == 200
    assert client.get("/flasgger_static/swagger-ui-bundle.js").status_code == 200
    assert client.get("/flasgger_static/swagger-ui-standalone-preset.js").status_code == 200


def test_refresh_logout_revokes_refresh_cookie(client):
    client.post("/setup/admin", json={"nome": "Admin", "email": "a@example.com", "senha": "SenhaForte#2026"})
    login = client.post("/auth/login", json={"email": "a@example.com", "senha": "SenhaForte#2026"})
    refresh = client.post("/auth/refresh")
    assert refresh.status_code == 200
    logout = client.post("/auth/logout")
    assert logout.status_code == 200
    assert client.post("/auth/refresh").status_code == 401
