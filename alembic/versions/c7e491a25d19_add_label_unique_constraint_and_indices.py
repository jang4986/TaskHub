"""add label unique constraint and indices

Revision ID: c7e491a25d19
Revises: 855c5789636e
Create Date: 2026-11-18 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e491a25d19'
down_revision: Union[str, Sequence[str], None] = '855c5789636e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('labels', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_labels_project_name', ['project_id', 'name'])

    with op.batch_alter_table('task_labels', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_task_labels_label_id'), ['label_id'], unique=False)

    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.create_index('ix_comments_task_created_id', ['task_id', 'created_at', 'id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.drop_index('ix_comments_task_created_id')

    with op.batch_alter_table('task_labels', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_task_labels_label_id'))

    with op.batch_alter_table('labels', schema=None) as batch_op:
        batch_op.drop_constraint('uq_labels_project_name', type_='unique')
