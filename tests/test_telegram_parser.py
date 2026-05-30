import json

from src.ingest.parsers.telegram import TelegramParser


def test_telegram_result_json(tmp_path):
    export_dir = tmp_path / "chat"
    export_dir.mkdir()
    data = {
        "name": "Test Chat",
        "type": "personal_chat",
        "messages": [
            {"type": "message", "date": "2025-01-01", "from": "Alice", "text": "Hello vault"},
        ],
    }
    path = export_dir / "result.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    docs = TelegramParser().extract(path)
    assert len(docs) == 1
    assert "Hello vault" in docs[0].text
    assert docs[0].extra_metadata.get("platform") == "telegram"
