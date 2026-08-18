"""translate plan notification links to the spanish routes

The notifications of the improvement plan module were built pointing at
``/plans/{id}``, a route the SPA does not have — its routes are Spanish
(``/planes/{id}``), so clicking one of those notifications opened a 404.
The builder is fixed; this repairs the links already stored.

Revision ID: f3c1b9d0a2e7
Revises: d18a4c7be902
Create Date: 2026-08-18 14:05:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f3c1b9d0a2e7'
down_revision: Union[str, Sequence[str], None] = 'd18a4c7be902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Point the stored notifications at the route the app really serves."""

    op.execute(
        """
        UPDATE notifications
        SET link = regexp_replace(link, '^/plans/', '/planes/')
        WHERE link LIKE '/plans/%'
        """
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Only the plan detail links came from the old builder: `/planes/nuevo`
    # and friends were always Spanish and must be left alone.
    op.execute(
        """
        UPDATE notifications
        SET link = regexp_replace(link, '^/planes/', '/plans/')
        WHERE link ~ '^/planes/\\d+$'
        """
    )
