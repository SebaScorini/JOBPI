"""Add storage_path column to cvs.

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("cvs")}
    if "storage_path" not in existing_columns:
        op.add_column("cvs", sa.Column("storage_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("cvs")}
    if "storage_path" in existing_columns:
        op.drop_column("cvs", "storage_path")
