"""Graph memory — entity relationships stored in Neo4j.

Entities : Person, Project, Organisation, Topic
Relations: MANAGES, WORKS_ON, DELAYED_BY, REPORTS_TO, PREFERS, DISLIKES

Neo4j is optional — if NEO4J_URI is not set the functions are no-ops so the
rest of the memory system continues to work normally.
"""

from __future__ import annotations

import logging
import re

from app.config import settings

logger = logging.getLogger(__name__)

# Driver is created on first use (lazy) so a missing/unreachable Neo4j
# instance never prevents the application from starting.
_driver = None


def _get_driver():
    global _driver
    if _driver is not None:
        return _driver

    if not settings.NEO4J_URI:
        return None

    try:
        from neo4j import AsyncGraphDatabase
        _driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        logger.info("Neo4j driver initialised — graph memory active")
    except Exception as exc:
        logger.warning("Neo4j unavailable, graph memory disabled: %s", exc)
        _driver = None

    return _driver


async def close() -> None:
    global _driver
    if _driver:
        await _driver.close()
        _driver = None


def _sanitize_rel_type(relation: str) -> str:
    rel = relation.strip().upper()
    rel = re.sub(r"[^A-Z0-9]+", "_", rel)
    return rel.strip("_") or "RELATED_TO"


async def upsert_entity(
    user_id: str,
    entity_type: str,
    name: str,
    properties: dict | None = None,
) -> None:
    driver = _get_driver()
    if not driver:
        return

    props = properties or {}
    query = (
        f"MERGE (e:{entity_type} {{name: $name, user_id: $user_id}}) "
        "SET e += $props, e.updated_at = timestamp()"
    )
    try:
        async with driver.session() as session:
            await session.run(query, name=name, user_id=user_id, props=props)
    except Exception as exc:
        logger.warning("Neo4j upsert_entity failed: %s", exc)


async def upsert_relation(
    user_id: str,
    from_entity: str,
    from_type: str,
    relation: str,
    to_entity: str,
    to_type: str,
    properties: dict | None = None,
) -> None:
    driver = _get_driver()
    if not driver:
        return

    props = properties or {}
    rel_type = _sanitize_rel_type(relation)
    query = f"""
        MERGE (a:{from_type} {{name: $from_name, user_id: $user_id}})
        MERGE (b:{to_type}  {{name: $to_name,   user_id: $user_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        SET r += $props, r.updated_at = timestamp()
    """
    try:
        async with driver.session() as session:
            await session.run(
                query,
                from_name=from_entity,
                to_name=to_entity,
                user_id=user_id,
                props=props,
            )
    except Exception as exc:
        logger.warning("Neo4j upsert_relation failed: %s", exc)


async def get_entity_context(user_id: str, entity_name: str) -> list[dict]:
    driver = _get_driver()
    if not driver:
        return []

    query = """
        MATCH (a {user_id: $user_id, name: $name})-[r]-(b)
        RETURN type(r) AS relation,
               labels(a)[0] AS from_type, a.name AS from_name,
               labels(b)[0] AS to_type,   b.name AS to_name
        LIMIT 20
    """
    try:
        async with driver.session() as session:
            result = await session.run(query, user_id=user_id, name=entity_name)
            return [dict(record) async for record in result]
    except Exception as exc:
        logger.warning("Neo4j get_entity_context failed: %s", exc)
        return []


async def search_entities(user_id: str, keyword: str) -> list[dict]:
    driver = _get_driver()
    if not driver:
        return []

    query = """
        MATCH (e {user_id: $user_id})
        WHERE toLower(e.name) CONTAINS toLower($keyword)
        RETURN labels(e)[0] AS type, e.name AS name
        LIMIT 10
    """
    try:
        async with driver.session() as session:
            result = await session.run(query, user_id=user_id, keyword=keyword)
            return [dict(record) async for record in result]
    except Exception as exc:
        logger.warning("Neo4j search_entities failed: %s", exc)
        return []
