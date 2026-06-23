"""expand settings description column

Revision ID: b3f6d9a1c2ef
Revises: 147602d8a083
Create Date: 2026-06-23 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f6d9a1c2ef"
down_revision: Union[str, Sequence[str], None] = "147602d8a083"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "settings",
        "description",
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "settings",
        "description",
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=True,
    )
