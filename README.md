# Gestão de estoque de livros

Backend REST em Flask com SQLite, SQLAlchemy ORM, Alembic, validação Pydantic e Swagger. O frontend será servido pelo próprio Flask sem build step e sem Node.

## Requisitos

- Python 3.12
- Windows PowerShell (os comandos abaixo também podem ser adaptados para macOS/Linux)

## Instalação e execução local

```powershell
cd C:\Users\ALUNO\Downloads\FrontEnd\ProjetoCodex
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite `.env` e substitua `SECRET_KEY` e `JWT_SECRET_KEY` por valores aleatórios longos. Para gerar uma chave no PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

O modo de desenvolvimento usa `AUTO_MIGRATE=1`, então `flask run --debug` cria o banco local e aplica as migrations ao iniciar. Também é possível preparar o banco explicitamente:

```powershell
flask db upgrade
flask run --debug
```

Swagger UI: <http://127.0.0.1:5000/apidocs>. Especificação OpenAPI/Swagger: <http://127.0.0.1:5000/apispec_1.json>.

## Primeiro administrador

Via API, antes do login:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/setup/admin `
  -ContentType 'application/json' `
  -Body '{"nome":"Admin","email":"admin@exemplo.com","senha":"SenhaForte#2026"}'
```

A rota só funciona enquanto a tabela de usuários estiver vazia. Uma repetição retorna `403`. A senha exige no mínimo 12 caracteres, letras maiúsculas e minúsculas, número e símbolo. Alternativamente, use `flask create-admin --email admin@exemplo.com`; a senha é solicitada sem eco.

## Autenticação

`POST /auth/login` devolve um access JWT com validade de 15 minutos. Use-o como `Authorization: Bearer <access_token>`. O refresh JWT é enviado em cookie `HttpOnly`, `SameSite=Strict`; `/auth/refresh` troca o cookie por outro access token e `/auth/logout` revoga o refresh token.

Rotas de escrita de livros exigem access token de usuário com papel `admin`. Leituras da coleção são públicas. Consulte `docs/API.md` e `docs/SETUP_ADMIN.md` para exemplos e fluxos.

## Banco de dados e migrations

SQLite fica em `instance/livros.db`. `flask db upgrade` usa Alembic e pode ser executado novamente sem reaplicar migrations concluídas. Para produção, configure `AUTO_MIGRATE=0`, `COOKIE_SECURE=1`, chaves secretas próprias e `FRONTEND_ORIGIN` com a origem real; aplique `flask db upgrade` como etapa de deploy. Não publique o arquivo `.env` nem a base SQLite.

## Produção

Gunicorn é disponibilizado para ambientes Unix/Linux:

```sh
gunicorn --workers 3 --bind 0.0.0.0:8000 run:app
```

Configure HTTPS no proxy reverso, use `COOKIE_SECURE=1` para habilitar cookies Secure, HSTS e redirecionamento HTTPS do Talisman, e aponte `RATELIMIT_STORAGE_URI` para Redis para compartilhar os limites entre workers. `memory://` atende somente desenvolvimento local e não sincroniza contadores entre processos.

As respostas de erro não incluem stack trace, SQL ou exceções internas. O log privado do servidor registra exceções inesperadas para diagnóstico. A CSP usa `unsafe-inline` em script/style para a inicialização da UI embutida do Flasgger; o frontend próprio usa arquivos estáticos externos e não insere dados do usuário em HTML.

## Testes

```powershell
python -m pytest -q
```
