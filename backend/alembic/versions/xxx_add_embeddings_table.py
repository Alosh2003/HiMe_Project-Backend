"""add embeddings table

Revision ID: xxx_add_embeddings
Revises: 3441dfe1be3d
Create Date: 2026-10-03

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "xxx_add_embeddings"
down_revision = "3441dfe1be3d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "embeddings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("entity_type", sa.String(length=20), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("embedding_vector", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column(
            "model_version",
            sa.String(length=50),
            nullable=False,
            server_default="all-MiniLM-L6-v2",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.UniqueConstraint(
            "entity_type", "entity_id", name="uq_entity_type_id"
        ),
    )
    op.create_index("ix_embeddings_id", "embeddings", ["id"])
    op.create_index("ix_embeddings_entity_id", "embeddings", ["entity_id"])
    op.create_index(
        "ix_embeddings_entity",
        "embeddings",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_embeddings_model",
        "embeddings",
        ["model_version"],
    )


def downgrade():
    op.drop_index("ix_embeddings_entity_id", table_name="embeddings")
    op.drop_index("ix_embeddings_id", table_name="embeddings")
    op.drop_index("ix_embeddings_model", table_name="embeddings")
    op.drop_index("ix_embeddings_entity", table_name="embeddings")
    op.drop_table("embeddings")
