from unittest.mock import patch

import numpy as np
from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()


def test_status_command():
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "PersonalRAGVault status" in result.stdout


def test_ingest_no_files(tmp_path):
    result = runner.invoke(app, ["ingest", str(tmp_path), "--allow-outside-home"])
    assert result.exit_code == 1


@patch("src.cli.embed_texts")
@patch("src.cli.build_documents_from_folder")
def test_ingest_success(mock_build, mock_embed, tmp_path):
    emb = np.random.rand(1, 384).astype(np.float32)
    mock_embed.return_value = emb
    mock_build.return_value = [
        {
            "id": "abc",
            "text": "hello",
            "metadata": {"source": str(tmp_path / "f.txt"), "chunk_index": 0, "total_chunks": 1},
        }
    ]
    result = runner.invoke(
        app,
        ["--quiet", "ingest", str(tmp_path), "--allow-outside-home"],
    )
    assert result.exit_code == 0


@patch("src.cli.search")
@patch("src.cli.embed_query")
def test_query_no_llm(mock_embed, mock_search):
    mock_embed.return_value = np.zeros(384, dtype=np.float32)
    mock_search.return_value = [
        {
            "text": "retrieved chunk",
            "metadata": {"source": "/tmp/x.txt"},
            "distance": 0.1,
        }
    ]
    result = runner.invoke(app, ["--quiet", "query", "what is RAG?", "--no-llm"])
    assert result.exit_code == 0
    assert "retrieved chunk" in result.stdout


@patch("src.cli.check_ollama_model")
@patch("src.cli.generate_answer")
@patch("src.cli.search")
@patch("src.cli.embed_query")
def test_query_with_ollama(mock_embed, mock_search, mock_gen, mock_check):
    mock_embed.return_value = np.zeros(384, dtype=np.float32)
    mock_search.return_value = [{"text": "ctx", "metadata": {"source": "/a"}, "distance": 0.2}]
    mock_gen.return_value = "An answer"
    result = runner.invoke(app, ["--quiet", "query", "test?"])
    assert result.exit_code == 0
    assert "An answer" in result.stdout
