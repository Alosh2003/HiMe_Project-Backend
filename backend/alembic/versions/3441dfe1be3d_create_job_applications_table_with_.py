"""create job_applications table with unique constraint

Revision ID: 3441dfe1be3d
Revises: c36d7c740716
Create Date: 2026-10-02 19:26:48.870264

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3441dfe1be3d'
down_revision: Union[str, Sequence[str], None] = 'c36d7c740716'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # إنشاء جدول job_applications مع القيد الفريد
    op.create_table(
        'job_applications',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('seeker_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('job_seekers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('applied_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('job_id', 'seeker_id', name='uq_job_seeker_application')
    )


def downgrade() -> None:
    op.drop_table('job_applications')
