"""unique plan per teacher and origin period

``ImprovementPlanService.create`` already refused a second plan for the same
teacher and origin period, but a check in Python is not a guarantee: two
requests can both pass it before either commits, and nothing in the schema
stopped the duplicate from landing.

The constraint also indexes the two accesses that had none — ``has_plan_for``
and ``_teachers_with_plan`` — and, leading with ``teacher_id``, it answers
lookups by teacher alone, which is what ``ix_improvement_plans_teacher_id`` was
there for. That one is dropped: keeping both would leave the same redundancy
the previous revision removed.

Revision ID: 37865bd16e61
Revises: 7d9da94bebb3
Create Date: 2026-09-03 21:58:44.812033

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "37865bd16e61"
down_revision: Union[str, Sequence[str], None] = "7d9da94bebb3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "uq_improvement_plan_teacher_period",
        "improvement_plans",
        ["teacher_id", "origin_period_id"],
    )
    op.drop_index(
        op.f("ix_improvement_plans_teacher_id"), table_name="improvement_plans"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index(
        op.f("ix_improvement_plans_teacher_id"),
        "improvement_plans",
        ["teacher_id"],
        unique=False,
    )
    op.drop_constraint(
        "uq_improvement_plan_teacher_period",
        "improvement_plans",
        type_="unique",
    )
