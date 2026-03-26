"""
Local shim for zep_cloud.external_clients.ontology
EntityModel, EntityText, EdgeModel — used by graph_builder to define ontology.
We accept these as pure metadata; actual extraction is done by LLM.
"""
from pydantic import BaseModel
from typing import Optional, Any


class EntityText(str):
    """Marker type for entity text attributes."""
    pass


class EntityModel(BaseModel):
    """Base class for entity type definitions."""
    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def get_description(cls) -> str:
        return cls.__doc__ or cls.__name__


class EdgeModel(BaseModel):
    """Base class for edge/relationship type definitions."""
    model_config = {"arbitrary_types_allowed": True}

    @classmethod
    def get_description(cls) -> str:
        return cls.__doc__ or cls.__name__
