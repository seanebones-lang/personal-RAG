from src.eval.metrics import aggregate, dcg_at_k, ndcg_at_k, score_retrieval
from src.eval.runner import run_evaluation


def test_score_retrieval_hit():
    results = [
        {"metadata": {"source": "/home/user/invoice.pdf", "file_name": "invoice.pdf"}},
    ]
    hit, rr, ndcg = score_retrieval(results, "invoice.pdf", top_k=5)
    assert hit is True
    assert rr == 1.0
    assert ndcg == 1.0


def test_score_retrieval_miss():
    results = [{"metadata": {"source": "/tmp/other.txt"}}]
    hit, rr, ndcg = score_retrieval(results, "invoice", top_k=5)
    assert hit is False
    assert rr == 0.0
    assert ndcg == 0.0


def test_ndcg_partial():
    results = [
        {"metadata": {"source": "/tmp/wrong.txt"}},
        {"metadata": {"source": "/tmp/invoice.pdf", "file_name": "invoice.pdf"}},
    ]
    assert ndcg_at_k(results, "invoice", 2) > 0.0
    assert ndcg_at_k(results, "invoice", 2) < 1.0


def test_dcg():
    assert dcg_at_k([1.0, 0.0], 2) > 0


def test_aggregate_ndcg():
    from src.eval.metrics import EvalResult

    rows = [
        EvalResult("q", True, 1.0, 1.0, "a"),
        EvalResult("q2", False, 0.0, 0.0, "b"),
    ]
    s = aggregate(rows)
    assert s["ndcg_at_k"] == 0.5


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
    assert payload["summary"]["ndcg_at_k"] == 1.0


def test_eval_generate_heuristic(tmp_path, monkeypatch):
    from src.eval.generate import generate_dataset

    monkeypatch.setattr(
        "src.eval.generate.sample_chunks_from_folder",
        lambda *a, **k: [
            {
                "text": "The capital of France is Paris.",
                "metadata": {"source": str(tmp_path / "notes.md"), "file_name": "notes.md"},
            }
        ],
    )
    rows = generate_dataset(
        path=tmp_path,
        sample=1,
        use_ollama=False,
        from_vault=False,
    )
    assert len(rows) == 1
    assert rows[0]["generated"] is True
    assert "notes.md" in rows[0]["expected_source_contains"]
