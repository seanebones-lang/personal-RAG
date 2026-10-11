"""Run with the wheel-installed interpreter, from a directory outside the checkout."""

import importlib.metadata
import os
import subprocess
import sys
import tempfile
from pathlib import Path

expected = sys.argv[1]
original_directory = Path.cwd()
with tempfile.TemporaryDirectory(prefix="prv-installed-") as directory:
    os.chdir(directory)
    try:
        # Import the installed package, not the source next to this script.
        sys.path.pop(0)
        from fastapi.testclient import TestClient

        import src
        from src.query.api import app

        installed = Path(src.__file__).resolve()
        assert any(part in ("site-packages", "dist-packages") for part in installed.parts), installed
        assert src.__version__ == expected == importlib.metadata.version("personalragvault")
        client = TestClient(app)
        assert client.get("/health").json()["status"] == "ok"
        assert client.get("/version").json()["version"] == expected
        assert client.get("/openapi.json").json()["info"]["version"] == expected
        for args in (["--version"], ["--help"], ["query", "--help"], ["ui", "--help"]):
            result = subprocess.run(
                [sys.executable, "-m", "src.cli", *args], check=True,
                capture_output=True, text=True,
            )
            if args == ["--version"]:
                assert result.stdout.strip() == f"PersonalRAGVault {expected}", result.stdout
        import streamlit
        assert Path(src.__file__).parent.joinpath("ui/app.py").is_file()
        assert streamlit.__version__
        print(f"Installed {expected}: CLI, API version/health, OpenAPI and UI files passed.")

    finally:
        # Windows cannot remove the process's working directory.
        os.chdir(original_directory)
