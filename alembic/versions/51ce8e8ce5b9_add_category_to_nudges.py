"""add_category_to_nudges

Revision ID: 51ce8e8ce5b9
Revises: d94c6425d85e
Create Date: 2026-03-13 16:52:37.939492

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '51ce8e8ce5b9'
down_revision: Union[str, Sequence[str], None] = 'd94c6425d85e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('partner_nudges', sa.Column('category', sa.String(length=50), nullable=False, server_default='General'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('partner_nudges', 'category')
