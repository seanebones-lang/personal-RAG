# Install PersonalRAGVault

PersonalRAGVault is a local Python application, free under the MIT license. Start
with the included sample before indexing personal documents.

## Requirements

- Git and Python **3.10–3.12**. The current CI runs on Python 3.11; other supported
  versions should also be checked before relying on a particular platform.
- Disk space for Python dependencies and embedding model downloads. The initial
  installation includes a CPU machine-learning runtime and can exceed 500 MB.
- Internet access for installation and the first model download.
- Ollama is optional; retrieval-only search needs no model API account.

## macOS and Linux

```bash
git clone https://github.com/seanebones-lang/personal-RAG.git
cd personal-RAG
./scripts/setup.sh --ui
./scripts/try-demo.sh
source .venv/bin/activate
```

Setup chooses a supported Python already installed on the machine. To select one:

```bash
PRV_PYTHON=python3.11 ./scripts/setup.sh --ui
```

An existing `.venv` must also use a supported Python. For contributors, add `--dev`.
For CLI-only use, omit `--ui`. The install is from this repository; no package
registry publication is assumed.

## Windows PowerShell

Choose an installed supported Python, for example Python 3.11:

```powershell
git clone https://github.com/seanebones-lang/personal-RAG.git
cd personal-RAG
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[ui]"
$env:PRV_DB_PATH = "$PWD\.demo-vault\chroma"
$env:PRV_LLM_PROVIDER = "ollama"
personalragvault ingest docs/assets/demo-sample --force
personalragvault query "What was the January invoice total?" --no-llm --hybrid
personalragvault ui
```

These Windows instructions describe the supported workflow; validate it on your
machine. Do not change an organization-managed PowerShell policy to run this app.

## First browser search

```bash
PRV_DB_PATH="$PWD/.demo-vault/chroma" PRV_LLM_PROVIDER=ollama personalragvault ui
```

Open `http://127.0.0.1:8501`. Select **Query**, check **Retrieval only**, and search
for the January invoice total. Inspect the matching sample text and source path.
See [TRY_DEMO.md](docs/TRY_DEMO.md) for expectations and limitations.

## Your documents and optional answers

Follow [getting started](docs/getting-started.md) for selecting a small folder,
previewing ingestion, querying, and optionally configuring Ollama. To add the
browser interface later, run `python -m pip install -e ".[ui]"` from this checkout.

The default personal index is `~/.personalragvault/chroma`. The demo uses a separate
`.demo-vault/chroma` directory. An explicitly configured external generation
provider receives retrieved context for generated answers. Use `--no-llm` for
retrieval without generation-provider requests.

## Release status

The current source package is **1.5.0**. Historical GitHub release labels are not a
version-matched distribution of this source. Install from source until a matching
release is prepared and verified; avoid choosing an archive by its label alone.

## Troubleshooting

Run `personalragvault status` and `personalragvault doctor`. Doctor can check the
configured generation provider; an unavailable Ollama does not prevent
retrieval-only search. See [FAQ](docs/faq.md) and [configuration](docs/configuration.md).
