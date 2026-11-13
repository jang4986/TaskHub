"""add_slug_and_description_to_workspaces

Revision ID: 855c5789636e
Revises: fd06e8388ea1
Create Date: 2026-11-13 17:13:27.131526

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '855c5789636e'
down_revision: Union[str, Sequence[str], None] = 'fd06e8388ea1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('slug', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.create_index(batch_op.f('ix_workspaces_slug'), ['slug'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workspaces_slug'))
        batch_op.drop_column('description')
        batch_op.drop_column('slug')
