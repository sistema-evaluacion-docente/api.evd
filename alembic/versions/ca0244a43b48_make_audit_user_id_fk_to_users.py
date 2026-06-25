"""make audit_user_id_fk_to_users

Revision ID: ca0244a43b48
Revises: 931a06663459
Create Date: 2026-06-25 10:40:37.902545

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca0244a43b48'
down_revision: Union[str, Sequence[str], None] = '931a06663459'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Clear non-numeric user_id values before altering column type
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE audit SET user_id = NULL WHERE user_id IS NOT NULL AND user_id !~ '^\\d+$'"
        )
    )
    op.alter_column(
        "audit",
        "user_id",
        existing_type=sa.VARCHAR(length=255),
        type_=sa.Integer(),
        existing_nullable=True,
        postgresql_using="user_id::integer",
    )
    op.create_index(op.f("ix_audit_user_id"), "audit", ["user_id"], unique=False)
    op.create_foreign_key(None, "audit", "users", ["user_id"], ["id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, "audit", type_="foreignkey")
    op.drop_index(op.f("ix_audit_user_id"), table_name="audit")
    op.alter_column(
        "audit",
        "user_id",
        existing_type=sa.Integer(),
        type_=sa.VARCHAR(length=255),
        existing_nullable=True,
    )
