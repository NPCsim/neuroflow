"""Add rollover fields and activity_log table

Revision ID: 1c46dba62544
Revises: 0b35cba51433
Create Date: 2026-10-26 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c46dba62544'
down_revision: Union[str, Sequence[str], None] = '0b35cba51433'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('carry_over_count', sa.Integer(), nullable=False, server_default='0'))

    with op.batch_alter_table('schedule_blocks', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=32), nullable=False, server_default='planned'))

    op.create_table(
        'activity_log',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=True),
        sa.Column('schedule_block_id', sa.String(length=36), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['schedule_block_id'], ['schedule_blocks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('activity_log')
    with op.batch_alter_table('schedule_blocks', schema=None) as batch_op:
        batch_op.drop_column('status')
    with op.batch_alter_table('tasks', schema=None) as batch_op:
        batch_op.drop_column('carry_over_count')
