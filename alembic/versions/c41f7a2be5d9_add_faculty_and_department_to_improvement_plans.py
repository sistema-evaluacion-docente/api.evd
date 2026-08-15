"""add faculty and department name to improvement plans

The header table of Formatos 2 and 3 prints FACULTAD and DEPARTAMENTO
ACADÉMICO. Until now both were read from the teacher record at render time, so
the printed form drifted whenever the teacher moved department. The director now
fills them in when the plan is created; the teacher record stays as the fallback
for plans created before this migration.

Revision ID: c41f7a2be5d9
Revises: 06c9289cc329
Create Date: 2026-08-14 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c41f7a2be5d9'
down_revision: Union[str, Sequence[str], None] = '06c9289cc329'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'improvement_plans',
        sa.Column('faculty_name', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'improvement_plans',
        sa.Column('department_name', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('improvement_plans', 'department_name')
    op.drop_column('improvement_plans', 'faculty_name')
