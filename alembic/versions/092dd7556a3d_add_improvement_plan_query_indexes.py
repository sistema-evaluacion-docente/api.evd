"""add improvement plan query indexes

Indexes for the two access patterns ``improvement_plans`` had none for:

* ``get_all`` filters by ``department_id`` (the director's scoping) and orders
  by ``created_at DESC``. A composite index serves both from a single walk.
* ``origin_period_id`` and ``verification_period_id`` are foreign keys with no
  index, so every delete or key update on ``academic_periods`` had to scan the
  whole table to check them.

Revision ID: 092dd7556a3d
Revises: c9d3f1a7b204
Create Date: 2026-09-03 21:11:57.404181

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "092dd7556a3d"
down_revision: Union[str, Sequence[str], None] = "c9d3f1a7b204"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_improvement_plans_department_created",
        "improvement_plans",
        ["department_id", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_improvement_plans_origin_period_id"),
        "improvement_plans",
        ["origin_period_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_improvement_plans_verification_period_id"),
        "improvement_plans",
        ["verification_period_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_improvement_plans_verification_period_id"),
        table_name="improvement_plans",
    )
    op.drop_index(
        op.f("ix_improvement_plans_origin_period_id"),
        table_name="improvement_plans",
    )
    op.drop_index(
        "ix_improvement_plans_department_created",
        table_name="improvement_plans",
    )
