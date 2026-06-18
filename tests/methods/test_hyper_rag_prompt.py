"""Unit tests for Hyper_RAG extraction prompts."""

from hyperextract.methods.rag.hyper_rag import Hyper_RAG_NODE_EXTRACTION_PROMPT


def test_hyper_rag_node_prompt_requests_concrete_entities():
    prompt = Hyper_RAG_NODE_EXTRACTION_PROMPT.lower()

    assert "person" in prompt
    assert "location" in prompt or "geo" in prompt
    assert "event" in prompt
    assert "only return an empty list" in prompt
