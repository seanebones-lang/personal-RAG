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



# New retrieval metrics test suite
def test_precision_at_k():
    from src.eval.metrics import precision_at_k
    results = [
        {"metadata": {"source": "invoice.pdf"}},
        {"metadata": {"source": "other.txt"}},
    ]
    assert precision_at_k(results, "invoice", 2) == 0.5
    assert precision_at_k(results, "invoice", 1) == 1.0

def test_average_precision():
    from src.eval.metrics import average_precision
    results = [
        {"metadata": {"source": "wrong.txt"}},
        {"metadata": {"source": "invoice.pdf"}},
    ]
    ap = average_precision(results, "invoice", 2)
    assert 0 < ap <= 1.0

def test_context_relevance():
    from src.eval.metrics import context_relevance
    results = [{"text": "The invoice total for January is high."}]
    score = context_relevance(results, "invoice total January", k=1)
    assert score > 0.5

def test_aggregate_new_metrics():
    from src.eval.metrics import EvalResult, aggregate
    rows = [EvalResult("q", True, 1.0, 1.0, "a")]
    s = aggregate(rows)
    assert "precision_at_k" in s
    assert "map" in s


# New generation quality test suite (heuristic-based)
def test_generation_quality_heuristic():
    # Placeholder for generation eval: simple overlap faithfulness/relevance
    query = "What is the capital of France?"
    answer = "The capital of France is Paris."
    context = "France's capital city is Paris."
    # Simple token overlap as proxy for faithfulness
    ans_terms = set(answer.lower().split())
    ctx_terms = set(context.lower().split())
    faithfulness = len(ans_terms & ctx_terms) / max(1, len(ans_terms))
    assert faithfulness >= 0.5
    # Answer relevance to query
    q_terms = set(query.lower().split())
    rel = len(ans_terms & q_terms) / max(1, len(q_terms))
    assert rel > 0.3
