"""add_institutional_code_to_directors

Revision ID: 6690ea2e2b66
Revises: ab815a23440b
Create Date: 2026-07-21 18:07:00.823516

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6690ea2e2b66'
down_revision: Union[str, Sequence[str], None] = 'ab815a23440b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "directors",
        sa.Column("institutional_code", sa.String(length=255), nullable=True),
    )
    op.create_index(
        op.f("ix_directors_institutional_code"),
        "directors",
        ["institutional_code"],
        unique=True,
    )
    op.execute(
        "UPDATE directors SET institutional_code = 'DIR' || id WHERE institutional_code IS NULL"
    )
    op.alter_column(
        "directors",
        "institutional_code",
        existing_type=sa.String(length=255),
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_directors_institutional_code"), table_name="directors")
    op.drop_column("directors", "institutional_code")
