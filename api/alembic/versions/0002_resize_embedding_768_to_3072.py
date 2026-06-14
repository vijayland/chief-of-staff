"""resize embedding vector 768 -> 3072 for gemini-embedding-001

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-14
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # lock_timeout prevents hanging on Neon if another connection holds a table lock
    op.execute("SET lock_timeout = '10s'")
    op.execute("DROP INDEX IF EXISTS ix_memory_nodes_embedding")
    op.execute("ALTER TABLE memory_nodes DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE memory_nodes ADD COLUMN embedding vector(3072)")
    # IVFFlat index skipped here — create it manually after loading data:
    # CREATE INDEX ix_memory_nodes_embedding ON memory_nodes
    # USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_memory_nodes_embedding")
    op.execute("ALTER TABLE memory_nodes DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE memory_nodes ADD COLUMN embedding vector(768)")
