"""drop duplicate primary key indexes on improvement plans

Every model in the module declared its primary key as
``mapped_column(Integer, primary_key=True, index=True)``. The primary key
already creates a unique B-tree over ``id``; ``index=True`` created a second,
non-unique one over the same single column. Both were maintained on every
INSERT, UPDATE and DELETE, and only one of the two was ever used — on
``improvement_plans`` the planner had answered 135 scans from ``ix_..._id``
while the primary key index sat at zero.

Dropping them costs nothing: a lookup by ``id`` falls back to the primary key
index, which is the same structure and additionally enforces uniqueness.

Revision ID: 7d9da94bebb3
Revises: 092dd7556a3d
Create Date: 2026-09-03 21:36:12.550194

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7d9da94bebb3"
down_revision: Union[str, Sequence[str], None] = "092dd7556a3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Every table of the module: each one carried an ``ix_<table>_id`` duplicating
# its own primary key index.
TABLES = (
    "improvement_plans",
    "improvement_plan_items",
    "improvement_plan_item_comments",
    "improvement_plan_courses",
    "improvement_plan_checkpoints",
    "improvement_plan_checkpoint_notes",
    "improvement_plan_documents",
    "improvement_plan_case_reports",
    "improvement_plan_evidences",
    "improvement_plan_evidence_requests",
    "improvement_plan_evidence_comments",
    "improvement_plan_verifications",
    "improvement_plan_verification_items",
    "improvement_plan_verification_courses",
    "improvement_plan_verification_comments",
)


def upgrade() -> None:
    """Upgrade schema."""
    for table in TABLES:
        op.drop_index(op.f(f"ix_{table}_id"), table_name=table)


def downgrade() -> None:
    """Downgrade schema."""
    for table in reversed(TABLES):
        op.create_index(op.f(f"ix_{table}_id"), table, ["id"], unique=False)
