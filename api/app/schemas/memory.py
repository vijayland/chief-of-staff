
from pydantic import BaseModel, Field

from app.db.models.memory_node import MemoryType


class MemoryResponse(BaseModel):
    id: str
    memory_type: MemoryType
    content: str
    source: str | None
    importance: float
    access_count: int
    created_at: str

    model_config = {"from_attributes": True}


class MemorySearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=50)


class MemorySearchResult(BaseModel):
    memory: MemoryResponse
    similarity: float


class UpdateMemoryRequest(BaseModel):
    importance: float = Field(ge=0.0, le=1.0)
