"""resize embedding vector 3072 -> 1536 for text-embedding-3-small

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-14
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("SET lock_timeout = '10s'")
    op.execute("DROP INDEX IF EXISTS ix_memory_nodes_embedding")
    op.execute("ALTER TABLE memory_nodes DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE memory_nodes ADD COLUMN embedding vector(1536)")
    # Also clear old embeddings since they're incompatible dimensions
    op.execute("DELETE FROM memory_nodes WHERE embedding IS NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_memory_nodes_embedding")
    op.execute("ALTER TABLE memory_nodes DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE memory_nodes ADD COLUMN embedding vector(3072)")
