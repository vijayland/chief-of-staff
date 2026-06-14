import uuid
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    google_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    preferred_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    oauth_tokens: Mapped[list["OAuthToken"]] = relationship(
        "OAuthToken", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )
    memory_nodes: Mapped[list["MemoryNode"]] = relationship(
        "MemoryNode", back_populates="user", cascade="all, delete-orphan"
    )
