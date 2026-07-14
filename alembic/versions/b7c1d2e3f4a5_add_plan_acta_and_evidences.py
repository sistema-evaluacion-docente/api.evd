"""add acta columns to improvement_plans and improvement_plan_evidences table

Revision ID: b7c1d2e3f4a5
Revises: f484d9628fbd
Create Date: 2026-07-13 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'f484d9628fbd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Guarded with existence checks because ``Base.metadata.create_all`` on app
    startup may have already created the new table (it never adds columns to
    existing tables, so the ALTERs below are still required)."""

    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_columns = {
        column["name"] for column in inspector.get_columns("improvement_plans")
    }

    if 'acta_pdf_url' not in existing_columns:
        op.add_column('improvement_plans', sa.Column('acta_pdf_url', sa.Text(), nullable=True))
    if 'acta_description' not in existing_columns:
        op.add_column('improvement_plans', sa.Column('acta_description', sa.Text(), nullable=True))
    if 'acta_uploaded_at' not in existing_columns:
        op.add_column('improvement_plans', sa.Column('acta_uploaded_at', sa.DateTime(timezone=True), nullable=True))

    if inspector.has_table('improvement_plan_evidences'):
        return

    op.create_table('improvement_plan_evidences',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('plan_id', sa.Integer(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=True),
    sa.Column('uploaded_by', sa.Integer(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('file_url', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['plan_id'], ['improvement_plans.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['item_id'], ['improvement_plan_items.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_improvement_plan_evidences_id'), 'improvement_plan_evidences', ['id'], unique=False)
    op.create_index(op.f('ix_improvement_plan_evidences_plan_id'), 'improvement_plan_evidences', ['plan_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_improvement_plan_evidences_plan_id'), table_name='improvement_plan_evidences')
    op.drop_index(op.f('ix_improvement_plan_evidences_id'), table_name='improvement_plan_evidences')
    op.drop_table('improvement_plan_evidences')

    op.drop_column('improvement_plans', 'acta_uploaded_at')
    op.drop_column('improvement_plans', 'acta_description')
    op.drop_column('improvement_plans', 'acta_pdf_url')
