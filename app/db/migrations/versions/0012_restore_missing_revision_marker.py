"""Restore missing Alembic revision marker.

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-20

This migration intentionally performs no schema changes.

Production is currently stamped at revision ``0012``, but that revision file is
missing from the repository history available to this checkout. Reintroducing
the revision as a no-op restores Alembic continuity so existing databases can
boot again and new databases can still migrate through the full chain.
"""

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op compatibility revision."""


def downgrade() -> None:
    """No-op compatibility revision."""
