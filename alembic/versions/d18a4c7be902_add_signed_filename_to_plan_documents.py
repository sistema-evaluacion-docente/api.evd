"""add signed filename to improvement plan documents

The signed scan is stored under a uuid path, so the interface had no name to
show for it. The director now sees the file he actually picked, as a chip he can
preview, download or remove; rows created before this migration keep a null name
and fall back to a generic one.

Revision ID: d18a4c7be902
Revises: c41f7a2be5d9
Create Date: 2026-08-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd18a4c7be902'
down_revision: Union[str, Sequence[str], None] = 'c41f7a2be5d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'improvement_plan_documents',
        sa.Column('signed_filename', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('improvement_plan_documents', 'signed_filename')
