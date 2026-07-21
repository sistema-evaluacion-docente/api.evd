"""remove_username_from_users

Revision ID: b07428384676
Revises: 6690ea2e2b66
Create Date: 2026-07-21 18:21:09.261262

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b07428384676'
down_revision: Union[str, Sequence[str], None] = '6690ea2e2b66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("users", "username")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "users",
        sa.Column("username", sa.String(length=255), nullable=True),
    )
    op.execute("UPDATE users SET username = email WHERE username IS NULL")
    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(length=255),
        nullable=False,
    )
