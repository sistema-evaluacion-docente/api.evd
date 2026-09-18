"""add deans table

Association between a user and the faculty they are dean of, mirroring
``directors`` (user_id + department_id) with ``faculty_id`` instead.

Revision ID: d7a00845ea35
Revises: d19b3c1ce0b8
Create Date: 2026-09-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a00845ea35'
down_revision: Union[str, Sequence[str], None] = 'd19b3c1ce0b8'
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

    if "deans" not in _existing_tables():
        op.create_table(
            'deans',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('faculty_id', sa.Integer(), nullable=False),
            sa.Column('active', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.ForeignKeyConstraint(['faculty_id'], ['faculties.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id'),
            sa.UniqueConstraint('faculty_id'),
        )
        op.create_index(op.f('ix_deans_user_id'), 'deans', ['user_id'], unique=True)
        op.create_index(op.f('ix_deans_faculty_id'), 'deans', ['faculty_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""

    if "deans" in _existing_tables():
        op.drop_table('deans')
