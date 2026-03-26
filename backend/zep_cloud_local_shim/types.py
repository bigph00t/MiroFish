"""
Data types matching the zep_cloud SDK surface used by MiroFish.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, List
from datetime import datetime


class InternalServerError(Exception):
    """Matches zep_cloud.InternalServerError for retry logic in zep_paging.py"""

    pass


@dataclass
class EpisodeData:
    """Input episode for graph.add_batch()"""

    data: str
    type: str = "text"


@dataclass
class EntityEdgeSourceTarget:
    """Source/target type pair for edge ontology definitions."""

    source: str
    target: str


@dataclass
class Episode:
    """Returned from graph.add_batch() and graph.episode.get()"""

    uuid_: str
    data: str
    type: str = "text"
    entity_count: int = 0
    processed: bool = True  # Local shim processes episodes synchronously
    created_at: Optional[datetime] = None


@dataclass
class Node:
    """Graph node — returned by graph.node.get() and graph.node.get_by_graph_id()"""

    uuid_: str
    name: str
    label: str = ""
    summary: str = ""
    attributes: dict = field(default_factory=dict)
    created_at: Optional[datetime] = None

    # Alias for code that uses .uuid
    @property
    def uuid(self):
        return self.uuid_

    @property
    def labels(self):
        """Return label as a list for compatibility with code that expects .labels"""
        return [self.label] if self.label else []


@dataclass
class Edge:
    """Graph edge — returned by graph.edge.get_by_graph_id() and search()"""

    uuid_: str
    fact: str
    source_node_uuid: str = ""
    target_node_uuid: str = ""
    attributes: dict = field(default_factory=dict)
    valid_at: Optional[datetime] = None
    invalid_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @property
    def uuid(self):
        return self.uuid_

    @property
    def name(self):
        """Return fact as name for compatibility"""
        return self.fact


@dataclass
class SearchResults:
    """Returned by graph.search()"""

    edges: List[Edge] = field(default_factory=list)
    nodes: List[Node] = field(default_factory=list)
