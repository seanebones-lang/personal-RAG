from src.ollama_client import build_context


def test_build_context_respects_max_chars():
    results = [
        {"text": "a" * 500},
        {"text": "b" * 500},
        {"text": "c" * 500},
    ]
    ctx = build_context(results, max_chars=600)
    assert len(ctx) <= 600
