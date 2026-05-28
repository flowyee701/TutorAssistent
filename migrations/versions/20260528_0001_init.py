"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2026-05-28

Первая миграция: создаёт всю схему по Base.metadata.
Последующие миграции — через `alembic revision --autogenerate`.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from core.db.models import Base

revision: str = "0001_init"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
