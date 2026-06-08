"""add audit, departments and users tables

Revision ID: caec06954064
Revises:
Create Date: 2026-06-08 10:22:42.617776

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "caec06954064"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "audit",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=True),
        sa.Column("table_name", sa.String(length=255), nullable=True),
        sa.Column("operation", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_id"), "audit", ["id"], unique=False)

    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("faculty", sa.String(length=255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_departments_code"), "departments", ["code"], unique=True)

    op.create_table(
        "users",
        sa.Column("uid", sa.Text(), nullable=False),
        sa.Column("institutional_code", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("uid"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(
        op.f("ix_users_institutional_code"),
        "users",
        ["institutional_code"],
        unique=True,
    )
    op.create_index(op.f("ix_users_uid"), "users", ["uid"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_users_uid"), table_name="users")
    op.drop_index(op.f("ix_users_institutional_code"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.drop_index(op.f("ix_departments_code"), table_name="departments")
    op.drop_table("departments")

    op.drop_index(op.f("ix_audit_id"), table_name="audit")
    op.drop_table("audit")
