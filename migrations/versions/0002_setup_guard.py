"""Serialize first administrator bootstrap attempts."""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa

revision = "0002_setup_guard"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    # Também permite prosseguir em instalações locais que já tinham a tabela
    # criada por create_all antes de esta revisão Alembic ser introduzida.
    if "setup_guard" not in inspect(op.get_bind()).get_table_names():
        op.create_table("setup_guard", sa.Column("id", sa.Integer(), nullable=False), sa.PrimaryKeyConstraint("id"))


def downgrade():
    if "setup_guard" in inspect(op.get_bind()).get_table_names():
        op.drop_table("setup_guard")
