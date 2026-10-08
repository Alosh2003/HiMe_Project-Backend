"""update user role enum and add oauth accounts

Revision ID: f2fbe7c57553
Revises: 1e0ba79e7e7b
Create Date: 2026-09-02 11:12:31.713685

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2fbe7c57553'
down_revision: Union[str, Sequence[str], None] = '1e0ba79e7e7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. إنشاء نوع الـ Enum أولاً في PostgreSQL
    user_role_enum = sa.Enum('company', 'job_seeker', name='user_role_enum')
    user_role_enum.create(op.get_bind(), checkfirst=True)

    # جدول oauth_accounts
    op.create_table(
        'oauth_accounts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('provider_account_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'provider_account_id', name='uq_provider_account')
    )

    # تعديل password_hash
    op.alter_column('users', 'password_hash',
               existing_type=sa.VARCHAR(),
               nullable=True)

    # 2. تحويل نوع العمود مع استخدام USING
    op.alter_column('users', 'role',
               existing_type=sa.VARCHAR(),
               type_=user_role_enum,
               postgresql_using='role::user_role_enum',
               existing_nullable=False)


def downgrade() -> None:
    user_role_enum = sa.Enum('company', 'job_seeker', name='user_role_enum')

    op.alter_column('users', 'role',
               existing_type=user_role_enum,
               type_=sa.VARCHAR(),
               existing_nullable=False)

    op.alter_column('users', 'password_hash',
               existing_type=sa.VARCHAR(),
               nullable=False)

    op.drop_table('oauth_accounts')

    # حذف نوع الـ Enum عند التراجع
    user_role_enum.drop(op.get_bind(), checkfirst=True)