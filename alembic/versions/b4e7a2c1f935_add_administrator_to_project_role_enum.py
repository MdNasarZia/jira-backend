"""add administrator to project_role_enum

Revision ID: b4e7a2c1f935
Revises: 9d9e22f43b8a
Create Date: 2026-03-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b4e7a2c1f935'
down_revision: Union[str, None] = '9d9e22f43b8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE project_role_enum ADD VALUE IF NOT EXISTS 'administrator'")


def downgrade() -> None:
    # PostgreSQL does not support removing a value from an enum type.
    # A full downgrade would require creating a replacement enum, migrating
    # all columns, and dropping the old type — which is destructive and
    # risky. Raise an error so the migration is not silently "reversed"
    # without manual intervention.
    raise NotImplementedError(
        "Cannot remove 'administrator' from project_role_enum. "
        "PostgreSQL does not support DROP VALUE on enum types. "
        "A manual migration is required to reverse this change."
    )
