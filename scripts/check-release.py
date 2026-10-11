"""Inspect release artifacts without importing application code or downloading models."""

import ast
import email
import hashlib
import sys
import tarfile
import zipfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
tree = ast.parse((root / "src/__init__.py").read_text())
version = next(
    ast.literal_eval(node.value)
    for node in tree.body
    if isinstance(node, ast.Assign)
    and any(isinstance(t, ast.Name) and t.id == "__version__" for t in node.targets)
)
if len(sys.argv) > 1 and sys.argv[1] != f"v{version}":
    raise SystemExit(f"Tag must match package version: v{version}")

dist = root / "dist"
wheel = dist / f"personalragvault-{version}-py3-none-any.whl"
source = dist / f"personalragvault-{version}.tar.gz"
with zipfile.ZipFile(wheel) as archive:
    metadata = email.message_from_bytes(
        archive.read(f"personalragvault-{version}.dist-info/METADATA")
    )
    assert metadata["Name"] == "personalragvault"
    assert metadata["Version"] == version
    assert metadata["License-Expression"] == "MIT"
    assert metadata["Requires-Python"] == "<3.13,>=3.10"
    assert "src/ui/app.py" in archive.namelist()
    assert not any(".env.local" in name or ".demo-vault" in name for name in archive.namelist())
with tarfile.open(source) as archive:
    prefix = f"personalragvault-{version}/"
    names = set(archive.getnames())
    for name in (
        "INSTALL.md", "LICENSE", "scripts/setup.sh", "scripts/try-demo.sh",
        "scripts/smoke-installed.py", "docs/TRY_DEMO.md", "docs/RELEASING.md",
        "docs/assets/demo-sample/notes.md",
    ):
        assert prefix + name in names, f"Missing first-use material: {name}"
    info = archive.getmember(prefix + "scripts/setup.sh")
    assert info.mode & 0o111, "Setup script must stay executable"
    metadata = email.message_from_bytes(archive.extractfile(prefix + "PKG-INFO").read())
    assert metadata["Version"] == version
    assert not any(".env.local" in name or ".demo-vault" in name for name in names)

checksums = "".join(
    f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
    for path in (wheel, source)
)
(dist / "SHA256SUMS").write_text(checksums)
print(f"Verified wheel/source version {version}, Python range and first-use contents.")

