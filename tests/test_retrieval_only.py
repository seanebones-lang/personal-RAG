from unittest.mock import Mock

import pytest

from src.config import reset_settings
from src.core import vault


@pytest.mark.parametrize("expansion_source", ["argument", "environment"])
def test_retrieval_only_never_calls_generation_for_query_expansion(monkeypatch, expansion_source):
    monkeypatch.setenv("PRV_LLM_PROVIDER", "openai")
    monkeypatch.setenv("PRV_MULTI_QUERY", "true")
    monkeypatch.setenv("PRV_EXPAND_QUERY_OLLAMA", str(expansion_source == "environment"))
    reset_settings()
    expand = Mock(side_effect=AssertionError("A retrieval-only query contacted generation"))
    generate = Mock(side_effect=AssertionError("A retrieval-only query generated an answer"))
    monkeypatch.setattr(vault, "expand_queries_ollama", expand)
    monkeypatch.setattr(vault, "generate_answer", generate)
    search = Mock(return_value=[{
        "id": "sample:1", "text": "The sample invoice total is $1,240.50.",
        "metadata": {"source": "sample.md"}, "distance": 0.1,
    }])
    monkeypatch.setattr(vault, "multi_query_search", search)

    result = vault.run_query(
        "What was the sample invoice total?", use_llm=False,
        expand_query=expansion_source == "argument",
    )

    assert result["results"][0]["metadata"]["source"] == "sample.md"
    assert result["answer"] is None
    assert len(search.call_args.args[0]) > 1  # Local heuristic variants still work.
    expand.assert_not_called()
    generate.assert_not_called()


def test_generation_enabled_can_still_expand_queries(monkeypatch):
    expand = Mock(return_value=["original query", "alternate query"])
    monkeypatch.setattr(vault, "expand_queries_ollama", expand)
    monkeypatch.setattr(vault, "multi_query_search", Mock(return_value=[]))

    vault.run_query("original query", use_llm=True, multi_query=True, expand_query=True)

    expand.assert_called_once_with("original query")
