import click
from flask.cli import with_appcontext
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Auditoria, Usuario
from app.schemas import AdminSetup
from app.security import hash_senha


@click.command("create-admin")
@click.option("--email", required=True, help="E-mail do primeiro administrador.")
@click.option("--name", "nome", default=None, help="Nome exibido (padrão: parte local do e-mail).")
@click.option("--password", "senha", prompt=True, hide_input=True, confirmation_prompt=True,
              help="Senha forte; evite passá-la na linha de comando para não expô-la no histórico.")
@with_appcontext
def create_admin_command(email, nome, senha):
    """Cria o primeiro administrador pelo terminal, se ainda não houver usuários."""
    if Usuario.query.first() is not None:
        raise click.ClickException("Já existe um usuário; o bootstrap está encerrado.")
    nome = nome or email.split("@", 1)[0]
    try:
        data = AdminSetup(nome=nome, email=email, senha=senha)
    except Exception as exc:
        raise click.ClickException("Dados inválidos ou senha fraca (12 caracteres com maiúscula, minúscula, número e símbolo).") from exc
    user = Usuario(nome=data.nome, email=str(data.email).lower(), senha_hash=hash_senha(data.senha), role="admin")
    from app.models import SetupGuard
    try:
        db.session.add(SetupGuard(id=1))
        db.session.add(user)
        db.session.flush()
    except IntegrityError as exc:
        db.session.rollback()
        raise click.ClickException("O bootstrap do administrador já foi iniciado ou concluído.") from exc
    # O comando não tem request web; registra que a origem foi CLI sem inventar um IP.
    db.session.add(Auditoria(usuario_id=user.id, acao="create", entidade="usuario", entidade_id=user.id,
                            ip="", user_agent="CLI"))
    db.session.commit()
    click.echo(f"Administrador criado: {user.email}")
