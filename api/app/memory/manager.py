"""MemoryManager — single facade the agent calls for all memory operations."""

import uuid
from dataclasses import dataclass, field
from sqlalchemy.ext.asyncio import AsyncSession
from app.memory import episodic, semantic, procedural, graph_store
from app.db.models.memory_node import MemoryType
from app.integrations.llm.client import get_embedding
from app.config import settings


@dataclass
class MemoryContext:
    facts: list[str] = field(default_factory=list)
    style_hints: list[str] = field(default_factory=list)
    recent_episodes: list[str] = field(default_factory=list)
    graph_context: list[dict] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        parts = []
        if self.facts:
            # Cap each fact at 200 chars, max 8 facts
            facts = [f[:200] for f in self.facts[:8]]
            parts.append("## Known facts & preferences\n" + "\n".join(f"- {f}" for f in facts))
        if self.style_hints:
            hints = [s[:150] for s in self.style_hints[:4]]
            parts.append("## Communication style\n" + "\n".join(f"- {s}" for s in hints))
        if self.recent_episodes:
            episodes = [e[:300] for e in self.recent_episodes[:2]]
            parts.append("## Recent context\n" + "\n".join(f"- {e}" for e in episodes))
        if self.graph_context:
            rel_lines = [
                f"- {r['from_name']} --[{r['relation']}]--> {r['to_name']}"
                for r in self.graph_context[:6]
            ]
            parts.append("## Entity relationships\n" + "\n".join(rel_lines))
        return "\n\n".join(parts)


class MemoryManager:
    def __init__(self, db: AsyncSession, user_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
        self.db = db
        self.user_id = user_id
        self.tenant_id = tenant_id

    async def retrieve(self, query: str, top_k: int | None = None) -> MemoryContext:
        """Retrieve all relevant memory for a query."""
        k = top_k or settings.MEMORY_MAX_CONTEXT_ITEMS

        # Compute embedding once and reuse across all memory type searches
        query_embedding = await get_embedding(query)

        fact_results = await semantic.search_similar(
            self.db, self.user_id, query, top_k=k,
            memory_type=MemoryType.semantic, query_embedding=query_embedding,
        )
        style_hints = await procedural.get_style_context(
            self.db, self.user_id, query, top_k=3, query_embedding=query_embedding,
        )
        recent = await episodic.get_recent_episodes(self.db, self.user_id, limit=3)

        return MemoryContext(
            facts=[n.content for n, _ in fact_results],
            style_hints=style_hints,
            recent_episodes=[n.content for n in recent],
        )

    async def store_fact(self, content: str, source: str = "chat", importance: float = 0.7) -> None:
        await semantic.upsert_fact(
            self.db, self.user_id, self.tenant_id, content, source, importance
        )

    async def store_style(self, pattern: str, source: str = "action") -> None:
        await procedural.record_style_pattern(
            self.db, self.user_id, self.tenant_id, pattern, source
        )

    async def store_episode(self, content: str, source: str = "chat") -> None:
        await episodic.store_episode(
            self.db, self.user_id, self.tenant_id, content, source
        )

    async def upsert_graph(
        self,
        from_entity: str,
        from_type: str,
        relation: str,
        to_entity: str,
        to_type: str,
    ) -> None:
        await graph_store.upsert_relation(
            str(self.user_id),
            from_entity, from_type,
            relation,
            to_entity, to_type,
        )

    async def get_graph_context(self, entity_name: str) -> list[dict]:
        return await graph_store.get_entity_context(str(self.user_id), entity_name)
