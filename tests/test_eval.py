from src.eval.metrics import score_retrieval
from src.eval.runner import run_evaluation


def test_score_retrieval_hit():
    results = [
        {"metadata": {"source": "/home/user/invoice.pdf", "file_name": "invoice.pdf"}},
    ]
    hit, rr = score_retrieval(results, "invoice.pdf", top_k=5)
    assert hit is True
    assert rr == 1.0


def test_score_retrieval_miss():
    results = [{"metadata": {"source": "/tmp/other.txt"}}]
    hit, rr = score_retrieval(results, "invoice", top_k=5)
    assert hit is False
    assert rr == 0.0


def test_run_evaluation_mocked(tmp_path, monkeypatch):
    ds = tmp_path / "eval.jsonl"
    ds.write_text(
        '{"question": "q1", "expected_source_contains": "a.txt"}\n',
        encoding="utf-8",
    )

    def fake_query(question, top_k=5, **kwargs):
        return {
            "results": [{"metadata": {"source": "/x/a.txt"}, "text": "hi"}],
            "context": "hi",
            "answer": None,
            "llm_error": None,
        }

    monkeypatch.setattr("src.eval.runner.run_query", fake_query)
    payload = run_evaluation(ds, top_k=5)
    assert payload["summary"]["hit_at_k"] == 1.0
