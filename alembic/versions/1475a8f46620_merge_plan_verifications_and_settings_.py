"""merge plan verifications and settings scope

Revision ID: 1475a8f46620
Revises: a5e2d81cf640, b8e4d21c7f90
Create Date: 2026-08-23 14:24:50.587810

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1475a8f46620'
down_revision: Union[str, Sequence[str], None] = ('a5e2d81cf640', 'b8e4d21c7f90')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
