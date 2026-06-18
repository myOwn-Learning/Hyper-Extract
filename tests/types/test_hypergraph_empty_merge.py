"""Unit tests for AutoHypergraph empty batch merge handling."""

from pydantic import BaseModel

from hyperextract.types import AutoHypergraph


class Entity(BaseModel):
    name: str
    type: str


class Event(BaseModel):
    participants: list[str]
    description: str


def test_merge_batch_data_handles_empty_chunk_lists(llm_client, embedder):
    hypergraph = AutoHypergraph(
        node_schema=Entity,
        edge_schema=Event,
        node_key_extractor=lambda x: x.name,
        edge_key_extractor=lambda x: tuple(sorted(x.participants)),
        nodes_in_edge_extractor=lambda x: x.participants,
        llm_client=llm_client,
        embedder=embedder,
    )

    merged = hypergraph.merge_batch_data(([[]], [[]]))

    assert merged.nodes == []
    assert merged.edges == []
