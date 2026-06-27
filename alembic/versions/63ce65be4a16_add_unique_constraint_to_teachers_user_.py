"""add_unique_constraint_to_teachers_user_id

Revision ID: 63ce65be4a16
Revises: ca0244a43b48
Create Date: 2026-06-27 10:36:43.456404

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63ce65be4a16'
down_revision: Union[str, Sequence[str], None] = 'ca0244a43b48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint('uq_teachers_user_id', 'teachers', ['user_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_teachers_user_id', 'teachers', type_='unique')
