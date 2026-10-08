"""add_blocked_until_to_users

Revision ID: a68d27798503
Revises: e33458270927
Create Date: 2026-09-09 15:03:16.553334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = 'a68d27798503'
down_revision: Union[str, Sequence[str], None] = 'e33458270927'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('users')]
    
    if 'blocked_until' not in columns:
        op.add_column('users', sa.Column('blocked_until', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'blocked_until')