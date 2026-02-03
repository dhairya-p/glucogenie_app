from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any, Dict, List

from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_neo4j_driver():
    """Return a singleton Neo4j driver if credentials are available."""
    uri = os.getenv("NEO4J_URI")
    username = os.getenv("NEO4J_USERNAME")
    password = os.getenv("NEO4J_PASSWORD")
    database = os.getenv("NEO4J_DATABASE", "neo4j")

    if not uri or not username or not password:
        logger.warning("[Neo4j] Missing connection settings; skipping Neo4j queries.")
        return None

    driver = GraphDatabase.driver(uri, auth=(username, password))
    logger.info("[Neo4j] Driver initialized for database '%s'", database)
    return driver


def query_kg_relationships(
    term: str,
    limit: int = 25,
    database: str | None = None,
) -> List[Dict[str, Any]]:
    """Query Neo4j for KG relationships related to a term.

    This is intentionally generic to support LlamaIndex KG storage. It does not
    assume a custom schema beyond node names and relationship types/properties.
    """
    driver = get_neo4j_driver()
    if driver is None:
        return []

    cypher = """
    MATCH (s)-[r]->(t)
    WHERE toLower(coalesce(s.name, s.id, "")) CONTAINS $term
       OR toLower(coalesce(t.name, t.id, "")) CONTAINS $term
    RETURN
        coalesce(s.name, s.id, "Unknown") AS subject,
        coalesce(r.rel, r.relationship, r.relation, r.predicate, type(r)) AS relation,
        coalesce(t.name, t.id, "Unknown") AS object,
        coalesce(r.source, r.source_doc, r.doc, "") AS source
    LIMIT $limit
    """

    term_norm = term.lower().strip()
    logger.info("[Neo4j] Querying KG for term='%s' (limit=%d)", term_norm, limit)
    results: List[Dict[str, Any]] = []

    try:
        with driver.session(database=database or os.getenv("NEO4J_DATABASE", "neo4j")) as session:
            rows = session.run(cypher, term=term_norm, limit=limit)
            for row in rows:
                results.append(
                    {
                        "subject": row.get("subject"),
                        "relation": row.get("relation"),
                        "object": row.get("object"),
                        "source": row.get("source"),
                    }
                )
    except Exception as exc:
        logger.error("[Neo4j] KG query failed: %s", exc, exc_info=True)
        return []

    logger.info("[Neo4j] KG query returned %d relationships", len(results))
    return results


def format_kg_context(results: List[Dict[str, Any]]) -> str:
    """Format Neo4j KG results into a citation-friendly context block."""
    if not results:
        return ""

    lines = [
        "Knowledge Graph Findings (with mandatory citations):",
        "Source: Neo4j Knowledge Graph (drug_interaction_docs)",
    ]
    for item in results[:25]:
        subject = item.get("subject", "Unknown")
        relation = item.get("relation", "RELATED_TO")
        obj = item.get("object", "Unknown")
        source = item.get("source")
        if source:
            lines.append(f"- {subject} {relation} {obj} (Source detail: {source})")
        else:
            lines.append(f"- {subject} {relation} {obj}")

    return "\n".join(lines)
