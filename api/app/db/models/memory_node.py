import uuid
from sqlalchemy import String, Text, Float, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base import Base, TimestampMixin, UUIDMixin
import enum


class MemoryType(str, enum.Enum):
    semantic = "semantic"      # facts & preferences
    procedural = "procedural"  # style & tone patterns
    episodic = "episodic"      # raw conversation summaries


class MemoryNode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "memory_nodes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    memory_type: Mapped[MemoryType] = mapped_column(
        SAEnum(MemoryType), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)  # chat|email|calendar|action
    importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    access_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # pgvector embedding column (1536 dims — text-embedding-3-small)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="memory_nodes")

    __table_args__ = ()
