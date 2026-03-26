"""
Local SQLite-backed graph store with LLM entity extraction and semantic search.
"""

import os
import json
import uuid
import sqlite3
import logging
import threading
from typing import Optional, List, Any
from datetime import datetime
from pathlib import Path

from .types import Episode, Node, Edge, EpisodeData, SearchResults

logger = logging.getLogger("mirofish.local_graph")

DB_PATH = Path.home() / ".mirofish" / "local_graph.db"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS graphs (
            graph_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            ontology TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS episodes (
            uuid_ TEXT PRIMARY KEY,
            graph_id TEXT,
            data TEXT,
            type TEXT,
            entity_count INTEGER DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS nodes (
            uuid_ TEXT PRIMARY KEY,
            graph_id TEXT,
            name TEXT,
            label TEXT,
            summary TEXT,
            attributes TEXT,
            embedding BLOB,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS edges (
            uuid_ TEXT PRIMARY KEY,
            graph_id TEXT,
            fact TEXT,
            source_node_uuid TEXT,
            target_node_uuid TEXT,
            valid_at TEXT,
            invalid_at TEXT,
            expired_at TEXT,
            embedding BLOB,
            created_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_nodes_graph ON nodes(graph_id);
        CREATE INDEX IF NOT EXISTS idx_edges_graph ON edges(graph_id);
        CREATE INDEX IF NOT EXISTS idx_episodes_graph ON episodes(graph_id);
        CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_node_uuid);
    """)
    conn.commit()


# Thread-local connection pool
_local = threading.local()


def get_conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = _get_conn()
        _init_db(_local.conn)
    return _local.conn


# ── LLM entity extraction ─────────────────────────────────────────────────────

EXTRACTION_PROMPT = """Extract entities and relationships from the following text.
Return a JSON object with this exact structure:
{
  "entities": [
    {"name": "Entity Name", "label": "EntityType", "summary": "Brief description"}
  ],
  "relationships": [
    {"source": "Entity Name A", "target": "Entity Name B", "fact": "A does/has/is X with/to B"}
  ]
}

Rules:
- Entities: people, places, organizations, concepts, events
- Labels: Person, Place, Organization, Concept, Event, Object
- Facts: short declarative sentences describing the relationship
- Be specific and extract all meaningful entities and relationships
- Return ONLY valid JSON, no other text

Text to analyze:
"""

_embedder = None
_embedder_lock = threading.Lock()


def get_embedder():
    global _embedder
    if _embedder is None:
        with _embedder_lock:
            if _embedder is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    logger.info(
                        "Loading sentence-transformers model (first run may download)..."
                    )
                    _embedder = SentenceTransformer("all-MiniLM-L6-v2")
                    logger.info("Embedder ready.")
                except Exception as e:
                    logger.warning(
                        f"sentence-transformers unavailable: {e}. Semantic search disabled."
                    )
                    _embedder = False
    return _embedder if _embedder else None


def embed_text(text: str) -> Optional[bytes]:
    embedder = get_embedder()
    if embedder is None:
        return None
    try:
        import numpy as np

        vec = embedder.encode(text, normalize_embeddings=True)
        return vec.astype("float32").tobytes()
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return None


def cosine_sim_bytes(a: bytes, b: bytes) -> float:
    import numpy as np

    va = np.frombuffer(a, dtype="float32")
    vb = np.frombuffer(b, dtype="float32")
    return float(np.dot(va, vb))  # already normalized


def _call_llm(prompt: str, text: str) -> Optional[dict]:
    """Call MiniMax (or configured LLM) to extract entities from text."""
    try:
        from openai import OpenAI

        api_key = os.environ.get("LLM_API_KEY", "")
        base_url = os.environ.get("LLM_BASE_URL", "https://api.minimax.io/v1")
        model = os.environ.get("LLM_MODEL_NAME", "MiniMax-M2.7")

        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt + text}],
            max_tokens=2048,
            temperature=0.1,
        )
        content = response.choices[0].message.content.strip()
        logger.info(f"Raw LLM response length: {len(content)}")

        # Handle empty or minimal content
        if not content or len(content) < 10:
            logger.warning(f"LLM returned empty or minimal content: '{content}'")
            return None

        # Strip  <think> ...<\/thinking> reasoning blocks (MiniMax-M2.7)
        import re

        content = re.sub(
            r"<thinking>.*?<\/thinking>", "", content, flags=re.DOTALL
        ).strip()

        # Also try alternative formats
        content = re.sub(
            r" <think> .*?<\/thinking>", "", content, flags=re.DOTALL
        ).strip()
        content = re.sub(
            r" <think> .*?$", "", content, flags=re.DOTALL | re.MULTILINE
        ).strip()

        # Strip markdown code fences if present
        if "```" in content:
            parts = content.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    content = part
                    break

        # Extract JSON object if there's surrounding text
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            content = match.group(0)

        # Check if we still have valid content
        if not content or len(content) < 10:
            logger.warning(f"Content too short after processing: '{content}'")
            return None

        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"LLM returned non-JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"LLM extraction failed: {e}")
        return None


# ── Graph operations ──────────────────────────────────────────────────────────


def create_graph(graph_id: str, name: str, description: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO graphs(graph_id, name, description, created_at) VALUES(?,?,?,?)",
        (graph_id, name, description, datetime.utcnow().isoformat()),
    )
    conn.commit()
    logger.info(f"Created local graph: {graph_id} ({name})")


def delete_graph(graph_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM edges WHERE graph_id=?", (graph_id,))
    conn.execute("DELETE FROM nodes WHERE graph_id=?", (graph_id,))
    conn.execute("DELETE FROM episodes WHERE graph_id=?", (graph_id,))
    conn.execute("DELETE FROM graphs WHERE graph_id=?", (graph_id,))
    conn.commit()
    logger.info(f"Deleted local graph: {graph_id}")


def set_ontology(graph_id: str, ontology: dict):
    """Store ontology metadata — we use it as context hints for extraction."""
    conn = get_conn()
    conn.execute(
        "UPDATE graphs SET ontology=? WHERE graph_id=?",
        (json.dumps(ontology), graph_id),
    )
    conn.commit()


def _upsert_node(conn, graph_id: str, name: str, label: str, summary: str) -> str:
    """Find or create a node by name+graph_id. Returns uuid_."""
    row = conn.execute(
        "SELECT uuid_ FROM nodes WHERE graph_id=? AND name=?", (graph_id, name)
    ).fetchone()
    if row:
        # Update summary if we got a better one
        if summary:
            conn.execute(
                "UPDATE nodes SET summary=? WHERE uuid_=? AND (summary='' OR summary IS NULL)",
                (summary, row["uuid_"]),
            )
        return row["uuid_"]

    node_id = str(uuid.uuid4())
    embedding = embed_text(f"{name} {label} {summary}")
    conn.execute(
        "INSERT INTO nodes(uuid_, graph_id, name, label, summary, attributes, embedding, created_at) VALUES(?,?,?,?,?,?,?,?)",
        (
            node_id,
            graph_id,
            name,
            label,
            summary,
            "{}",
            embedding,
            datetime.utcnow().isoformat(),
        ),
    )
    return node_id


def add_episodes_batch(graph_id: str, episodes: List[EpisodeData]) -> List[Episode]:
    """Add text episodes, extract entities/relationships via LLM, store in graph."""
    conn = get_conn()
    result_episodes = []

    for ep_data in episodes:
        ep_uuid = str(uuid.uuid4())
        text = ep_data.data

        logger.info(
            f"Extracting entities from episode {ep_uuid[:8]}... ({len(text)} chars)"
        )

        extracted = _call_llm(EXTRACTION_PROMPT, text)
        entity_count = 0

        if extracted:
            entities = extracted.get("entities", [])
            relationships = extracted.get("relationships", [])

            # Insert nodes
            node_id_map = {}
            for ent in entities:
                name = ent.get("name", "").strip()
                if not name:
                    continue
                label = ent.get("label", "Entity")
                summary = ent.get("summary", "")
                nid = _upsert_node(conn, graph_id, name, label, summary)
                node_id_map[name] = nid
                entity_count += 1

            # Insert edges
            for rel in relationships:
                src_name = rel.get("source", "").strip()
                tgt_name = rel.get("target", "").strip()
                fact = rel.get("fact", "").strip()
                if not fact or not src_name or not tgt_name:
                    continue

                src_id = node_id_map.get(src_name) or _upsert_node(
                    conn, graph_id, src_name, "Entity", ""
                )
                tgt_id = node_id_map.get(tgt_name) or _upsert_node(
                    conn, graph_id, tgt_name, "Entity", ""
                )

                edge_id = str(uuid.uuid4())
                embedding = embed_text(fact)
                conn.execute(
                    """INSERT INTO edges(uuid_, graph_id, fact, source_node_uuid, target_node_uuid, embedding, created_at)
                       VALUES(?,?,?,?,?,?,?)""",
                    (
                        edge_id,
                        graph_id,
                        fact,
                        src_id,
                        tgt_id,
                        embedding,
                        datetime.utcnow().isoformat(),
                    ),
                )

        # Store episode
        conn.execute(
            "INSERT INTO episodes(uuid_, graph_id, data, type, entity_count, created_at) VALUES(?,?,?,?,?,?)",
            (
                ep_uuid,
                graph_id,
                text,
                ep_data.type,
                entity_count,
                datetime.utcnow().isoformat(),
            ),
        )

        result_episodes.append(
            Episode(
                uuid_=ep_uuid, data=text, type=ep_data.type, entity_count=entity_count
            )
        )

    conn.commit()
    logger.info(f"Batch added {len(result_episodes)} episodes to graph {graph_id}")
    return result_episodes


def add_single(graph_id: str, data: str, type: str = "text"):
    """Add a single episode (used during simulation for memory updates)."""
    add_episodes_batch(graph_id, [EpisodeData(data=data, type=type)])


def get_episode(uuid_: str) -> Optional[Episode]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM episodes WHERE uuid_=?", (uuid_,)).fetchone()
    if not row:
        return None
    return Episode(
        uuid_=row["uuid_"],
        data=row["data"],
        type=row["type"],
        entity_count=row["entity_count"],
    )


def get_node(uuid_: str) -> Optional[Node]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM nodes WHERE uuid_=?", (uuid_,)).fetchone()
    if not row:
        return None
    return Node(
        uuid_=row["uuid_"],
        name=row["name"],
        label=row["label"] or "",
        summary=row["summary"] or "",
        attributes=json.loads(row["attributes"] or "{}"),
    )


def get_nodes_by_graph(
    graph_id: str, limit: int = 100, uuid_cursor: Optional[str] = None
) -> List[Node]:
    conn = get_conn()
    if uuid_cursor:
        rows = conn.execute(
            "SELECT * FROM nodes WHERE graph_id=? AND uuid_ > ? ORDER BY uuid_ LIMIT ?",
            (graph_id, uuid_cursor, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM nodes WHERE graph_id=? ORDER BY uuid_ LIMIT ?",
            (graph_id, limit),
        ).fetchall()
    return [
        Node(
            uuid_=r["uuid_"],
            name=r["name"],
            label=r["label"] or "",
            summary=r["summary"] or "",
            attributes=json.loads(r["attributes"] or "{}"),
        )
        for r in rows
    ]


def get_entity_edges(node_uuid: str) -> List[Edge]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM edges WHERE source_node_uuid=? OR target_node_uuid=?",
        (node_uuid, node_uuid),
    ).fetchall()
    return [
        Edge(
            uuid_=r["uuid_"],
            fact=r["fact"],
            source_node_uuid=r["source_node_uuid"],
            target_node_uuid=r["target_node_uuid"],
        )
        for r in rows
    ]


def get_edges_by_graph(
    graph_id: str, limit: int = 100, uuid_cursor: Optional[str] = None
) -> List[Edge]:
    conn = get_conn()
    if uuid_cursor:
        rows = conn.execute(
            "SELECT * FROM edges WHERE graph_id=? AND uuid_ > ? ORDER BY uuid_ LIMIT ?",
            (graph_id, uuid_cursor, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM edges WHERE graph_id=? ORDER BY uuid_ LIMIT ?",
            (graph_id, limit),
        ).fetchall()
    return [
        Edge(
            uuid_=r["uuid_"],
            fact=r["fact"],
            source_node_uuid=r["source_node_uuid"],
            target_node_uuid=r["target_node_uuid"],
        )
        for r in rows
    ]


def search_graph(
    graph_id: str, query: str, limit: int = 10, scope: str = "edges"
) -> SearchResults:
    """Semantic search using sentence-transformer embeddings + cosine similarity."""
    conn = get_conn()
    query_emb = embed_text(query)

    result_edges = []
    result_nodes = []

    if query_emb and scope in ("edges", "both"):
        rows = conn.execute(
            "SELECT * FROM edges WHERE graph_id=? AND embedding IS NOT NULL",
            (graph_id,),
        ).fetchall()
        scored = []
        for r in rows:
            sim = cosine_sim_bytes(query_emb, r["embedding"])
            scored.append((sim, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        for _, r in scored[:limit]:
            result_edges.append(
                Edge(
                    uuid_=r["uuid_"],
                    fact=r["fact"],
                    source_node_uuid=r["source_node_uuid"],
                    target_node_uuid=r["target_node_uuid"],
                )
            )

    if query_emb and scope in ("nodes", "both"):
        rows = conn.execute(
            "SELECT * FROM nodes WHERE graph_id=? AND embedding IS NOT NULL",
            (graph_id,),
        ).fetchall()
        scored = []
        for r in rows:
            sim = cosine_sim_bytes(query_emb, r["embedding"])
            scored.append((sim, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        for _, r in scored[:limit]:
            result_nodes.append(
                Node(
                    uuid_=r["uuid_"],
                    name=r["name"],
                    label=r["label"] or "",
                    summary=r["summary"] or "",
                    attributes=json.loads(r["attributes"] or "{}"),
                )
            )

    # Fallback: keyword search if no embeddings
    if not query_emb:
        kw = f"%{query}%"
        rows = conn.execute(
            "SELECT * FROM edges WHERE graph_id=? AND fact LIKE ? LIMIT ?",
            (graph_id, kw, limit),
        ).fetchall()
        result_edges = [
            Edge(
                uuid_=r["uuid_"],
                fact=r["fact"],
                source_node_uuid=r["source_node_uuid"],
                target_node_uuid=r["target_node_uuid"],
            )
            for r in rows
        ]

    return SearchResults(edges=result_edges, nodes=result_nodes)
