# Release and verify PersonalRAGVault

Use the same version in `src.__version__`, the GitHub tag (`v<version>`), and
the wheel/source metadata. Setuptools reads that version directly; do not add a
second static package version. The CLI reports it with `personalragvault --version`.

## Historical label

The old GitHub tag **v5.0** points to a checkout whose package metadata declares
**1.4.1**. That label is preserved for link compatibility; it is not a 5.x package
series. The matching release series resumes at **v1.5.1**. Do not move or delete
old tags to conceal the discrepancy. Installed dependencies remain governed by
their Python package metadata.

## Build and check

In a clean checkout with Python 3.10–3.12:

```bash
./scripts/setup.sh --ui --dev
python -m pip install build
ruff check src tests
pytest -m "not integration"
python -m build
python scripts/check-release.py v1.5.1
```

The artifact check requires a matching wheel and source distribution, the
declared Python range, the UI source and the runnable first-use materials. It
writes `dist/SHA256SUMS` for these two files. Build into a clean `dist` directory
or upload only the exact files checked; never upload a stale artifact by glob.

Install the wheel into a separate environment and run from outside the checkout:

```bash
python -m venv .venv-release
.venv-release/bin/python -m pip install "./dist/personalragvault-1.5.1-py3-none-any.whl[ui]" httpx
.venv-release/bin/python scripts/smoke-installed.py 1.5.1
```

On Windows use `.venv-release\Scripts\python.exe`. CI covers installed-wheel
checks on Linux and Windows plus unit tests on Linux with Python 3.10, 3.11 and
3.12. Those checks do not validate every parser, optional model or user collection.

Before publication, also extract the source archive, run its setup and synthetic
demo, and verify the fictional invoice total `$1,240.50` with its source path.
The demo downloads MiniLM embeddings on first use and makes no generation-provider
request. Use a temporary demo index, not a personal vault. Verify the installed
browser starts on loopback and the synthetic source preview works.

## Publish the checked artifacts

After reviewing and merging the release preparation and passing CI, create a
GitHub release at that exact reviewed commit. Attach the checked wheel, source
archive and `SHA256SUMS`; document validation, optional provider behavior and
platform limits in the release notes. Download the published assets and compare
each hash with the checksum file. Mark the matching release as latest explicitly
because the old misleading tag sorts higher numerically.

GitHub publication does not publish to PyPI. This repository currently documents
GitHub downloads and pinned source installation. Do not advertise a registry
command until that registry publication has independently been verified.
