# Install PersonalRAGVault

PersonalRAGVault is a local Python application, free under the MIT license. Start
with the included sample before indexing personal documents.

## Requirements

- Git and Python **3.10–3.12**. CI checks all three Python versions on Linux and installed wheels on Linux
  and Windows. Validate your own OS, collection, and optional integrations.
- Disk space for Python dependencies and embedding model downloads. The initial
  installation includes a CPU machine-learning runtime and can exceed 500 MB.
- Internet access for installation and the first model download.
- Ollama is optional; retrieval-only search needs no model API account.

## macOS and Linux

```bash
git clone --branch v1.5.1 --depth 1 https://github.com/seanebones-lang/personal-RAG.git
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
git clone --branch v1.5.1 --depth 1 https://github.com/seanebones-lang/personal-RAG.git
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

## Install from a verified download

Open the [v1.5.1 release](https://github.com/seanebones-lang/personal-RAG/releases/tag/v1.5.1).
Download `personalragvault-1.5.1.tar.gz` and `SHA256SUMS` into the same folder.
Verify the matching checksum line before extracting:

```bash
shasum -a 256 personalragvault-1.5.1.tar.gz
# Compare the full hash with that filename in SHA256SUMS.
tar -xzf personalragvault-1.5.1.tar.gz
cd personalragvault-1.5.1
./scripts/setup.sh --ui
./scripts/try-demo.sh
source .venv/bin/activate
personalragvault --version
```

The source archive includes setup scripts, the synthetic sample, and guides.
Git is not required for this downloaded-source path. On Windows, extract the
archive with your usual archive tool, then use the virtual-environment and pip
steps above from the extracted directory. PowerShell can compute the hash with
`Get-FileHash .\personalragvault-1.5.1.tar.gz -Algorithm SHA256`.

For developers who only need the installed CLI/API, download and verify
`personalragvault-1.5.1-py3-none-any.whl` instead. In an activated Python 3.10–3.12
virtual environment, run:

```bash
python -m pip install ./personalragvault-1.5.1-py3-none-any.whl
personalragvault --version
personalragvault --help
```

For the browser interface use
`python -m pip install "./personalragvault-1.5.1-py3-none-any.whl[ui]"`.
The wheel installs the application; the setup scripts and demo documents are in
the source archive. Dependencies and the first embedding-model download need
internet access. This is a Python release, not a standalone native executable or
a managed cloud service. No PyPI upload is assumed.

## Release history

The supported package version and GitHub tag match: **1.5.1 / v1.5.1**.
The historical tag `v5.0` contains package **1.4.1**. It remains intact so existing
links work; do not compare its label as though it were a package version.
Use the named release above and `personalragvault --version` to identify your build.

## Troubleshooting

Run `personalragvault status` and `personalragvault doctor`. Doctor can check the
configured generation provider; an unavailable Ollama does not prevent
retrieval-only search. See [FAQ](docs/faq.md) and [configuration](docs/configuration.md).
