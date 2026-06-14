"""Graph memory — entity relationships stored in Neo4j.

Entities: Person, Project, Organisation, Topic
Relations: MANAGES, WORKS_ON, DELAYED_BY, REPORTS_TO, PREFERS, DISLIKES
"""

from neo4j import AsyncGraphDatabase
from app.config import settings
import uuid

_driver = AsyncGraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
)


async def close() -> None:
    await _driver.close()


async def upsert_entity(
    user_id: str,
    entity_type: str,
    name: str,
    properties: dict | None = None,
) -> None:
    props = properties or {}
    query = (
        f"MERGE (e:{entity_type} {{name: $name, user_id: $user_id}}) "
        "SET e += $props, e.updated_at = timestamp()"
    )
    async with _driver.session() as session:
        await session.run(query, name=name, user_id=user_id, props=props)


def _sanitize_rel_type(relation: str) -> str:
    """Neo4j relationship types cannot contain spaces or special chars."""
    import re
    rel = relation.strip().upper()
    rel = re.sub(r"[^A-Z0-9]+", "_", rel)
    return rel.strip("_") or "RELATED_TO"


async def upsert_relation(
    user_id: str,
    from_entity: str,
    from_type: str,
    relation: str,
    to_entity: str,
    to_type: str,
    properties: dict | None = None,
) -> None:
    props = properties or {}
    rel_type = _sanitize_rel_type(relation)
    query = f"""
        MERGE (a:{from_type} {{name: $from_name, user_id: $user_id}})
        MERGE (b:{to_type}  {{name: $to_name,   user_id: $user_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $props, r.updated_at = timestamp()
    """
    async with _driver.session() as session:
        await session.run(
            query,
            from_name=from_entity,
            to_name=to_entity,
            user_id=user_id,
            props=props,
        )


async def get_entity_context(user_id: str, entity_name: str) -> list[dict]:
    """Return all relationships involving a named entity for this user."""
    query = """
        MATCH (a {user_id: $user_id, name: $name})-[r]-(b)
        RETURN type(r) AS relation, labels(a)[0] AS from_type, a.name AS from_name,
               labels(b)[0] AS to_type, b.name AS to_name
        LIMIT 20
    """
    async with _driver.session() as session:
        result = await session.run(query, user_id=user_id, name=entity_name)
        return [dict(record) async for record in result]


async def search_entities(user_id: str, keyword: str) -> list[dict]:
    query = """
        MATCH (e {user_id: $user_id})
        WHERE toLower(e.name) CONTAINS toLower($keyword)
        RETURN labels(e)[0] AS type, e.name AS name
        LIMIT 10
    """
    async with _driver.session() as session:
        result = await session.run(query, user_id=user_id, keyword=keyword)
        return [dict(record) async for record in result]
