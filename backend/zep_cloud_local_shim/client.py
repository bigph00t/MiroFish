"""
Local Zep client shim — mirrors zep_cloud.client.Zep interface used by MiroFish.
Backed by SQLite + LLM entity extraction + sentence-transformers search.
"""
import logging
from typing import Optional, List, Any

from .types import Episode, Node, Edge, EpisodeData, SearchResults
from . import store

logger = logging.getLogger("mirofish.local_graph")


class _EpisodeClient:
    def get(self, uuid_: str) -> Optional[Episode]:
        return store.get_episode(uuid_)


class _NodeClient:
    def get(self, uuid_: str) -> Optional[Node]:
        return store.get_node(uuid_)

    def get_by_graph_id(self, graph_id: str, limit: int = 100, uuid_cursor: Optional[str] = None) -> List[Node]:
        return store.get_nodes_by_graph(graph_id, limit=limit, uuid_cursor=uuid_cursor)

    def get_entity_edges(self, node_uuid: str) -> List[Edge]:
        return store.get_entity_edges(node_uuid)


class _EdgeClient:
    def get_by_graph_id(self, graph_id: str, limit: int = 100, uuid_cursor: Optional[str] = None) -> List[Edge]:
        return store.get_edges_by_graph(graph_id, limit=limit, uuid_cursor=uuid_cursor)


class _GraphClient:
    def __init__(self):
        self.episode = _EpisodeClient()
        self.node = _NodeClient()
        self.edge = _EdgeClient()

    def create(self, graph_id: str, name: str = "", description: str = "", **kwargs):
        store.create_graph(graph_id, name, description)

    def delete(self, graph_id: str, **kwargs):
        store.delete_graph(graph_id)

    def set_ontology(self, graph_ids: List[str], entities=None, edges=None, **kwargs):
        """Store ontology as metadata hints for entity extraction."""
        ontology = {}
        if entities:
            ontology["entities"] = {k: v.__doc__ for k, v in entities.items()} if isinstance(entities, dict) else str(entities)
        if edges:
            ontology["edges"] = {k: str(v) for k, v in edges.items()} if isinstance(edges, dict) else str(edges)
        for gid in graph_ids:
            store.set_ontology(gid, ontology)

    def add_batch(self, graph_id: str, episodes: List[EpisodeData], **kwargs) -> List[Episode]:
        return store.add_episodes_batch(graph_id, episodes)

    def add(self, graph_id: str, data: str, type: str = "text", **kwargs):
        store.add_single(graph_id, data, type)

    def search(
        self,
        graph_id: str,
        query: str,
        limit: int = 10,
        scope: str = "edges",
        reranker: Optional[str] = None,
        **kwargs
    ) -> SearchResults:
        return store.search_graph(graph_id, query, limit=limit, scope=scope)


class Zep:
    """
    Local drop-in for zep_cloud.client.Zep.
    api_key is accepted but ignored — all storage is local.
    """
    def __init__(self, api_key: Optional[str] = None, **kwargs):
        self.graph = _GraphClient()
        if api_key and api_key != "local":
            logger.info("Local Zep shim active — api_key ignored, using SQLite + LLM extraction")
        else:
            logger.info("Local Zep shim active")
