"""add programs table

Catalog of academic programs, identified by ``code`` (unique) and ``name``.

Revision ID: c9d3f1a7b204
Revises: 1475a8f46620
Create Date: 2026-08-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d3f1a7b204'
down_revision: Union[str, Sequence[str], None] = '1475a8f46620'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    """Tables already present in the database.

    ``api/app.py`` calls ``Base.metadata.create_all()`` on startup, so any
    developer who boots the app before migrating already has this table and a
    bare ``create_table`` would fail with DuplicateTable. See MIGRATIONS.md.
    """

    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    """Upgrade schema."""

    if "programs" not in _existing_tables():
        op.create_table(
            'programs',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('code', sa.String(length=255), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('code'),
        )


def downgrade() -> None:
    """Downgrade schema."""

    if "programs" in _existing_tables():
        op.drop_table('programs')
