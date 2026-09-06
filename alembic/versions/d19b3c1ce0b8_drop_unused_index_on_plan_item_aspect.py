"""drop unused index on plan item aspect

``improvement_plan_items.aspect`` was indexed, but no query filters, joins or
orders by it: the items of a plan are grouped under their aspect in Python,
after they have been loaded, in ``ImprovementPlanDocumentService.build_context``.
``pg_stat_user_indexes`` agreed — zero scans since the module went in.

An index nothing reads is still maintained on every write, so this is pure
write amplification on the table that gets rewritten every time a director
edits a plan.

Revision ID: d19b3c1ce0b8
Revises: ea5bef6c866a
Create Date: 2026-09-03 22:52:19.336704

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d19b3c1ce0b8"
down_revision: Union[str, Sequence[str], None] = "ea5bef6c866a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(
        op.f("ix_improvement_plan_items_aspect"),
        table_name="improvement_plan_items",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index(
        op.f("ix_improvement_plan_items_aspect"),
        "improvement_plan_items",
        ["aspect"],
        unique=False,
    )
