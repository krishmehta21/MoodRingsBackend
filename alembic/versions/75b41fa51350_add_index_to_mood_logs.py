"""add index to mood_logs

Revision ID: 75b41fa51350
Revises: f366c517332b
Create Date: 2026-03-11 14:18:07.432892

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75b41fa51350'
down_revision: Union[str, Sequence[str], None] = 'f366c517332b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('idx_mood_logs_user_date', 'mood_logs', ['user_id', 'logged_at'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_mood_logs_user_date', table_name='mood_logs')
