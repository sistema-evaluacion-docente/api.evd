"""merge heads

Revision ID: ec5d1df3ff55
Revises: 011fc109782c, d18a4c7be902
Create Date: 2026-08-17 22:58:05.350369

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec5d1df3ff55'
down_revision: Union[str, Sequence[str], None] = ('011fc109782c', 'd18a4c7be902')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
