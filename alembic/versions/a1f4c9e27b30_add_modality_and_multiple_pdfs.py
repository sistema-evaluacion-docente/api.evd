"""add modality to academic groups and allow several pdfs per evaluation

Revision ID: a1f4c9e27b30
Revises: 0d2e7905869f
Create Date: 2026-08-20 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1f4c9e27b30'
down_revision: Union[str, Sequence[str], None] = '0d2e7905869f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'academic_groups',
        sa.Column('modality', sa.String(length=20), nullable=True),
    )
    op.create_index(
        op.f('ix_academic_groups_modality'),
        'academic_groups',
        ['modality'],
        unique=False,
    )
    # An evaluation can now be backed by two PDFs, stored as comma-separated
    # paths, which no longer fit in the original varchar(255).
    op.alter_column(
        'evaluations',
        'pdf_url',
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Keep only the first path so the value fits back into varchar(255).
    op.execute(
        "UPDATE evaluations SET pdf_url = split_part(pdf_url, ',', 1) "
        "WHERE pdf_url LIKE '%,%'"
    )
    op.alter_column(
        'evaluations',
        'pdf_url',
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=True,
    )
    op.drop_index(op.f('ix_academic_groups_modality'), table_name='academic_groups')
    op.drop_column('academic_groups', 'modality')
