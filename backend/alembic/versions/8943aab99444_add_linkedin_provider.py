"""add linkedin provider 

Revision ID: 8943aab99444
Revises: ec6c115186b5
Create Date: 2026-09-10 21:24:55.159957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '8943aab99444'
down_revision: Union[str, Sequence[str], None] = 'ec6c115186b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. إنشاء نوع الـ Enum الجديد مباشرة في PostgreSQL
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'oauth_provider_enum') THEN
                CREATE TYPE oauth_provider_enum AS ENUM ('google', 'facebook', 'linkedin');
            END IF;
        END $$;
    """)

    # 2. تحويل نوع العمود مع تحويل القيم النصية
    op.execute("""
        ALTER TABLE oauth_accounts 
        ALTER COLUMN provider TYPE oauth_provider_enum 
        USING provider::text::oauth_provider_enum;
    """)


def downgrade() -> None:
    # 1. إنشاء النوع القديم إذا لم يكن موجوداً
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'oauthprovider') THEN
                CREATE TYPE oauthprovider AS ENUM ('google', 'facebook', 'linkedin');
            END IF;
        END $$;
    """)

    # 2. إعادة العمود للنوع القديم
    op.execute("""
        ALTER TABLE oauth_accounts 
        ALTER COLUMN provider TYPE oauthprovider 
        USING provider::text::oauthprovider;
    """)

    # 3. حذف النوع الجديد
    op.execute("DROP TYPE IF EXISTS oauth_provider_enum;")