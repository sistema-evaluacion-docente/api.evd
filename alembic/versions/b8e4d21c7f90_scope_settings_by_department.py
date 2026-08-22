"""scope settings by department

Adds ``department_id`` to settings and their history so every department can
keep its own value for a key. NULL stays the institutional value, which is the
fallback for any department that has not overridden the key.

Revision ID: b8e4d21c7f90
Revises: a1f4c9e27b30
Create Date: 2026-08-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8e4d21c7f90'
down_revision: Union[str, Sequence[str], None] = 'a1f4c9e27b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'settings',
        sa.Column('department_id', sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f('ix_settings_department_id'),
        'settings',
        ['department_id'],
        unique=False,
    )
    op.create_foreign_key(
        'fk_settings_department_id_departments',
        'settings',
        'departments',
        ['department_id'],
        ['id'],
        ondelete='CASCADE',
    )

    # `key` alone is no longer unique: the same key now exists once per scope.
    # The constraint name is the one Postgres derives from `unique=True`.
    op.execute('ALTER TABLE settings DROP CONSTRAINT IF EXISTS settings_key_key')
    op.create_index(op.f('ix_settings_key'), 'settings', ['key'], unique=False)
    op.create_unique_constraint(
        'uq_settings_key_department',
        'settings',
        ['key', 'department_id'],
    )
    # Postgres treats NULLs as distinct, so the constraint above does not stop
    # two institutional rows sharing a key — this partial index does.
    op.create_index(
        'uq_settings_key_global',
        'settings',
        ['key'],
        unique=True,
        postgresql_where=sa.text('department_id IS NULL'),
    )

    op.add_column(
        'settings_history',
        sa.Column('department_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_settings_history_department_id_departments',
        'settings_history',
        'departments',
        ['department_id'],
        ['id'],
        ondelete='CASCADE',
    )
    op.create_index(
        'ix_settings_history_key_department',
        'settings_history',
        ['key', 'department_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_settings_history_key_department', table_name='settings_history'
    )
    op.drop_constraint(
        'fk_settings_history_department_id_departments',
        'settings_history',
        type_='foreignkey',
    )
    op.drop_column('settings_history', 'department_id')

    # Only the institutional rows can survive a schema where `key` is unique
    # on its own.
    op.execute('DELETE FROM settings WHERE department_id IS NOT NULL')

    op.drop_index('uq_settings_key_global', table_name='settings')
    op.drop_constraint('uq_settings_key_department', 'settings', type_='unique')
    op.drop_index(op.f('ix_settings_key'), table_name='settings')
    op.drop_constraint(
        'fk_settings_department_id_departments', 'settings', type_='foreignkey'
    )
    op.drop_index(op.f('ix_settings_department_id'), table_name='settings')
    op.drop_column('settings', 'department_id')
    op.create_unique_constraint('settings_key_key', 'settings', ['key'])
