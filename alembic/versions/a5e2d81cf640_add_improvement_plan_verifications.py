"""add improvement plan verifications

A plan is closed when the Formato 3 is signed, which happens before the grades
that would prove the teacher improved exist. These tables hold the after-the-
fact answer, written when the evaluation of the verification period is
uploaded:

- ``improvement_plan_verifications`` — one row per (plan, verification period),
  filled in two passes: the scores when the evaluation finishes processing, the
  comment findings once the AI has classified them
- ``improvement_plan_verification_items`` — each agreed target measured again
- ``improvement_plan_verification_courses`` — the same indicator per subject of
  the new period, so a shortcoming that moved to another subject is still seen
- ``improvement_plan_verification_comments`` — comments of the new period that
  bring back the pedagogical category of a qualitative commitment

Nothing here touches the closing the director signed.

Revision ID: a5e2d81cf640
Revises: f3c1b9d0a2e7
Create Date: 2026-08-21 02:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5e2d81cf640'
down_revision: Union[str, Sequence[str], None] = 'f3c1b9d0a2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables() -> set[str]:
    """Tables already present in the database.

    ``api/app.py`` calls ``Base.metadata.create_all()`` on startup, so any
    developer who boots the app before migrating already has these tables and a
    bare ``create_table`` would fail with DuplicateTable. See MIGRATIONS.md.
    """

    return set(sa.inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    """Upgrade schema."""

    existing = _existing_tables()

    if "improvement_plan_verifications" not in existing:
        op.create_table(
            'improvement_plan_verifications',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('plan_id', sa.Integer(), nullable=False),
            sa.Column('period_id', sa.Integer(), nullable=False),
            sa.Column('evaluation_id', sa.Integer(), nullable=True),
            sa.Column('result', sa.String(length=20), nullable=False, server_default='SIN_DATOS'),
            sa.Column('scores_verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('comments_verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('scores_notified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('comments_notified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['plan_id'], ['improvement_plans.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['period_id'], ['academic_periods.id'], ),
            sa.ForeignKeyConstraint(['evaluation_id'], ['evaluations.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('plan_id', 'period_id', name='uq_plan_verification_plan_period'),
        )
        op.create_index(op.f('ix_improvement_plan_verifications_id'), 'improvement_plan_verifications', ['id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_verifications_plan_id'), 'improvement_plan_verifications', ['plan_id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_verifications_period_id'), 'improvement_plan_verifications', ['period_id'], unique=False)

    if "improvement_plan_verification_items" not in existing:
        op.create_table(
            'improvement_plan_verification_items',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('verification_id', sa.Integer(), nullable=False),
            sa.Column('item_id', sa.Integer(), nullable=True),
            sa.Column('target_type', sa.String(length=50), nullable=False),
            sa.Column('target_ref', sa.String(length=255), nullable=True),
            sa.Column('target_value', sa.Numeric(precision=4, scale=2), nullable=False),
            sa.Column('result_value', sa.Numeric(precision=4, scale=2), nullable=True),
            sa.Column('met', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['verification_id'], ['improvement_plan_verifications.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['item_id'], ['improvement_plan_items.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_improvement_plan_verification_items_id'), 'improvement_plan_verification_items', ['id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_verification_items_verification_id'), 'improvement_plan_verification_items', ['verification_id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_verification_items_item_id'), 'improvement_plan_verification_items', ['item_id'], unique=False)

    if "improvement_plan_verification_courses" not in existing:
        op.create_table(
            'improvement_plan_verification_courses',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('verification_item_id', sa.Integer(), nullable=False),
            sa.Column('academic_group_id', sa.Integer(), nullable=True),
            sa.Column('course_name', sa.String(length=255), nullable=True),
            sa.Column('course_code', sa.String(length=50), nullable=True),
            sa.Column('group_name', sa.String(length=50), nullable=True),
            sa.Column('result_value', sa.Numeric(precision=4, scale=2), nullable=False),
            sa.Column('met', sa.Boolean(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['verification_item_id'], ['improvement_plan_verification_items.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['academic_group_id'], ['academic_groups.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_improvement_plan_verification_courses_id'), 'improvement_plan_verification_courses', ['id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_verification_courses_verification_item_id'), 'improvement_plan_verification_courses', ['verification_item_id'], unique=False)

    if "improvement_plan_verification_comments" not in existing:
        op.create_table(
            'improvement_plan_verification_comments',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('verification_id', sa.Integer(), nullable=False),
            sa.Column('item_id', sa.Integer(), nullable=True),
            sa.Column('comment_id', sa.Integer(), nullable=False),
            sa.Column('pedagogical_category_id', sa.Integer(), nullable=True),
            sa.Column('category_name', sa.String(length=255), nullable=True),
            sa.Column('risk_level_name', sa.String(length=50), nullable=True),
            sa.Column('is_alert', sa.Boolean(), nullable=False, server_default=sa.text('false')),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['verification_id'], ['improvement_plan_verifications.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['item_id'], ['improvement_plan_items.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['pedagogical_category_id'], ['pedagogical_categories.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id'),
        )
        op.create_index(op.f('ix_improvement_plan_verification_comments_id'), 'improvement_plan_verification_comments', ['id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_verification_comments_verification_id'), 'improvement_plan_verification_comments', ['verification_id'], unique=False)
        op.create_index(op.f('ix_improvement_plan_verification_comments_item_id'), 'improvement_plan_verification_comments', ['item_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table('improvement_plan_verification_comments')
    op.drop_table('improvement_plan_verification_courses')
    op.drop_table('improvement_plan_verification_items')
    op.drop_table('improvement_plan_verifications')
