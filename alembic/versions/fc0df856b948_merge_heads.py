"""merge heads

Revision ID: fc0df856b948
Revises: ec5d1df3ff55, f3c1b9d0a2e7
Create Date: 2026-08-18 14:46:19.242204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc0df856b948'
down_revision: Union[str, Sequence[str], None] = ('ec5d1df3ff55', 'f3c1b9d0a2e7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
