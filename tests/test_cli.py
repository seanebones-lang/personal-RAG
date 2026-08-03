from unittest.mock import patch

from typer.testing import CliRunner

from src.cli import app
from src.config import reset_settings

runner = CliRunner()


def test_status_command():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "PersonalRAGVault status" in result.stdout
    assert "hybrid=" in result.stdout


@patch("src.cli.run_ingest", return_value=0)
def test_ingest_no_files(_mock_ingest, tmp_path):
    result = runner.invoke(app, ["ingest", str(tmp_path), "--allow-outside-home"])
    assert result.exit_code == 1


@patch("src.cli.run_ingest", return_value=3)
def test_ingest_success(_mock_ingest, tmp_path):
    result = runner.invoke(
        app,
        ["--quiet", "ingest", str(tmp_path), "--allow-outside-home"],
    )
    assert result.exit_code == 0


@patch("src.cli.run_query")
def test_query_no_llm(mock_run_query):
    mock_run_query.return_value = {
        "results": [
            {
                "text": "retrieved chunk",
                "metadata": {"source": "/tmp/x.txt"},
                "distance": 0.1,
            }
        ],
        "context": "retrieved chunk",
        "answer": None,
        "llm_error": None,
    }
    result = runner.invoke(app, ["--quiet", "query", "what is RAG?", "--no-llm"])
    assert result.exit_code == 0
    assert "retrieved chunk" in result.stdout
    assert mock_run_query.call_args.kwargs.get("hybrid") is False


@patch("src.cli.run_query")
def test_query_hybrid_env_default(mock_run_query, monkeypatch):
    monkeypatch.setenv("PRV_HYBRID", "true")
    reset_settings()
    mock_run_query.return_value = {
        "results": [{"text": "ctx", "metadata": {"source": "/a"}, "distance": 0.2}],
        "context": "ctx",
        "answer": None,
        "llm_error": None,
    }
    result = runner.invoke(app, ["--quiet", "query", "q?", "--no-llm"])
    assert result.exit_code == 0
    assert mock_run_query.call_args.kwargs.get("hybrid") is True
    result2 = runner.invoke(app, ["--quiet", "query", "q?", "--no-llm", "--no-hybrid"])
    assert result2.exit_code == 0
    assert mock_run_query.call_args.kwargs.get("hybrid") is False


@patch("src.cli.run_query")
def test_query_with_ollama(mock_run_query):
    mock_run_query.return_value = {
        "results": [{"text": "ctx", "metadata": {"source": "/a"}, "distance": 0.2}],
        "context": "ctx",
        "answer": "An answer",
        "llm_error": None,
    }
    result = runner.invoke(app, ["--quiet", "query", "test?"])
    assert result.exit_code == 0
    assert "An answer" in result.stdout


def test_models_list():
    result = runner.invoke(app, ["models", "list"])
    assert result.exit_code == 0
    assert "mini" in result.stdout


@patch("src.retrieval.graph.neighbors")
def test_graph_command(mock_neighbors):
    mock_neighbors.return_value = {
        "note": "Alpha",
        "source": "/v/Alpha.md",
        "direction": "both",
        "outbound": ["Beta"],
        "inbound": [],
        "neighbors": ["Beta"],
        "notes_indexed": 1,
        "edges": 1,
    }
    result = runner.invoke(app, ["graph", "Alpha"])
    assert result.exit_code == 0
    assert "Alpha" in result.stdout
    assert "Beta" in result.stdout
