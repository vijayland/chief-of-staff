"""resize embedding vector 512 -> 768 for Gemini text-embedding-004

Revision ID: 0001
Revises:
Create Date: 2026-06-14
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE memory_nodes DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE memory_nodes ADD COLUMN embedding vector(768)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_memory_nodes_embedding
        ON memory_nodes USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_memory_nodes_embedding")
    op.execute("ALTER TABLE memory_nodes DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE memory_nodes ADD COLUMN embedding vector(512)")
