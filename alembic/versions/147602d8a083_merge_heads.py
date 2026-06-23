"""merge heads

Revision ID: 147602d8a083
Revises: 4c1203f830f7, 8d011067bc34
Create Date: 2026-06-23 16:50:18.435530

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '147602d8a083'
down_revision: Union[str, Sequence[str], None] = ('4c1203f830f7', '8d011067bc34')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
