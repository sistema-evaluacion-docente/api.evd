"""index foreign keys checked on parent deletes

Postgres does not index a foreign key on its own. Whenever a parent row goes
away it has to find the children pointing at it, and with no index that search
is a sequential scan of the child table — once per deleted parent row, not once
per statement.

The six columns here are the ones whose parent is deleted as part of ordinary
use:

* ``comments`` — deleting an evaluation bulk deletes every comment it brought
  in (``EvaluationsRepository.delete_evaluation``), so a re-upload scanned
  ``improvement_plan_verification_comments`` once per comment.
  ``improvement_plan_item_comments`` already had its index.
* ``evaluations`` and ``academic_groups`` — deleted through their own endpoints,
  nulling out the traceability pointers that the plan and verification rows keep.
* ``improvement_plan_items`` — editing a plan replaces its item list, so items
  are deleted on a routine save and each one nulls the evidences and requests
  that referenced it.

Deliberately left unindexed: every ``users`` foreign key (``created_by``,
``uploaded_by``, ``reviewed_by``, ``signed_by``, ``generated_by``,
``requested_by``, ``author_id``, ``reported_by``, ``acta_closed_by``) — nothing
filters by them and users are not deleted — and
``verification_comments.pedagogical_category_id``, whose parent is a catalogue
of a handful of rows that only changes when the taxonomy itself does.

Revision ID: ea5bef6c866a
Revises: 37865bd16e61
Create Date: 2026-09-03 22:31:08.917245

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ea5bef6c866a"
down_revision: Union[str, Sequence[str], None] = "37865bd16e61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, column) — the index takes the ``ix_<table>_<column>`` name the models
# generate, so ``alembic check`` sees no drift.
FOREIGN_KEYS = (
    ("improvement_plan_verification_comments", "comment_id"),
    ("improvement_plan_verifications", "evaluation_id"),
    ("improvement_plan_courses", "academic_group_id"),
    ("improvement_plan_verification_courses", "academic_group_id"),
    ("improvement_plan_evidences", "item_id"),
    ("improvement_plan_evidence_requests", "item_id"),
)


def upgrade() -> None:
    """Upgrade schema."""
    for table, column in FOREIGN_KEYS:
        op.create_index(
            op.f(f"ix_{table}_{column}"), table, [column], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table, column in reversed(FOREIGN_KEYS):
        op.drop_index(op.f(f"ix_{table}_{column}"), table_name=table)
