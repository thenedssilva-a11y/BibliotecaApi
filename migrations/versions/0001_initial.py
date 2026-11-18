"""Create users, books, audit log and token revocation tables."""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("usuarios",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("nome", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False), sa.Column("senha_hash", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False), sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("email"))
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)
    op.create_table("livros",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("titulo", sa.String(length=200), nullable=False),
        sa.Column("autor", sa.String(length=160), nullable=False), sa.Column("isbn", sa.String(length=17), nullable=False),
        sa.Column("editora", sa.String(length=160), nullable=False), sa.Column("ano_publicacao", sa.Integer(), nullable=False),
        sa.Column("categoria", sa.String(length=80), nullable=False), sa.Column("preco", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("quantidade_estoque", sa.Integer(), nullable=False), sa.Column("descricao", sa.String(length=2000), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False), sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("isbn"))
    op.create_index("ix_livros_titulo", "livros", ["titulo"], unique=False)
    op.create_index("ix_livros_autor", "livros", ["autor"], unique=False)
    op.create_index("ix_livros_isbn", "livros", ["isbn"], unique=True)
    op.create_index("ix_livros_categoria", "livros", ["categoria"], unique=False)
    op.create_table("auditoria",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("acao", sa.String(length=40), nullable=False), sa.Column("entidade", sa.String(length=40), nullable=False),
        sa.Column("entidade_id", sa.Integer(), nullable=True), sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("user_agent", sa.String(length=500), nullable=False), sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]), sa.PrimaryKeyConstraint("id"))
    op.create_table("tokens_revogados",
        sa.Column("jti", sa.String(length=36), nullable=False), sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("jti"))


def downgrade():
    op.drop_table("tokens_revogados")
    op.drop_table("auditoria")
    op.drop_index("ix_livros_categoria", table_name="livros")
    op.drop_index("ix_livros_isbn", table_name="livros")
    op.drop_index("ix_livros_autor", table_name="livros")
    op.drop_index("ix_livros_titulo", table_name="livros")
    op.drop_table("livros")
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
