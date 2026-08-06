# ScryRaven

ScryRaven is a weird little grounded-search lab for chasing claims, checking sources, and making answers show their receipts.

It is a source-grounded research assistant experiment with a backend pipeline (`run_pipeline` in [`core/pipeline_orchestrator.py`](core/pipeline_orchestrator.py)) and a public command-line interface. It:

* Routes query intent across web, news, and academic-style research flows
* Generates targeted search queries
* Retrieves sources from configured search providers
* Ranks and filters evidence
* Synthesizes cited reports
* Experiments with source obligations, evidence sufficiency, and answer posture

The public CLI and backend pipeline are the current supported executable product interface. The legacy Streamlit shell has been retired. Its source under [`ui/`](ui/) is retained temporarily for reference and migration only, and [`app.py`](app.py) is now a fail-closed compatibility tombstone.

## Status

This repository is a cleaned public snapshot of a private research prototype. Some internal module names and historical validation notes may still reflect earlier working names. The public project name is now **ScryRaven**.

This is not a polished product. It is a working prototype and architecture lab for grounded answers, citation discipline, source-quality handling, and claim-aware retrieval.

No replacement UI framework has been selected. Future UI work should consume transport-neutral application services rather than the legacy Streamlit shell. The current CLI should not be read as a commitment to the final user experience.

## What It Does

For a query submitted through the public CLI, the backend can:

1. Classify the prompt
2. Plan search and retrieval work
3. Search across one or more configured providers
4. Fetch and chunk source text
5. Score evidence for relevance and source quality
6. Run analysis and audit passes depending on mode
7. Render a final markdown report with citations

The core idea is simple: not all citations count the same, and an answer should know when its evidence is not good enough.

## Requirements

* Python 3.10+; Python 3.11 is recommended
* API keys for at least:

  * `OPENAI_API_KEY`
  * `TAVILY_API_KEY`

Optional integrations:

* `OPENROUTER_API_KEY`
* `LINKUP_API_KEY`
* `EXA_API_KEY`
* `BRAVE_API_KEY`
* `SERPER_API_KEY`
* Local LM Studio endpoint, if using local models

## Setup

From the project root:

1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies

```powershell
pip install -r requirements.txt
```

3. Optional: install developer tools

```powershell
pip install -r requirements-dev.txt
```

4. Create your `.env` file

```powershell
copy .env.example .env
```

Then edit `.env` and set real values for your keys.

> Never commit `.env`, local output packets, logs, caches, database files, raw provider payloads, or private traces.

## How to Run

Normal query runs may call external services. Treat them as approval-gated when working in review or validation mode.

### Public CLI

```powershell
python -m scryraven "your query" --mode Balanced
```

The legacy compatibility entrypoint remains available:

```powershell
python -m proplex "your query" --mode Balanced
```

Use `python -m scryraven --help` for all CLI options. `python -m proplex --help` is preserved for existing scripts.

#### Bounded live-run configuration

The shared CLI accepts one explicit local authorization file when a maintainer
intends a bounded ordinary-product run:

```powershell
python -m scryraven "your query" --mode Balanced `
  --include-domains docs.python.org `
  --fast-provider OpenAI --fast-model <exact-model> `
  --smart-provider OpenAI --smart-model <exact-model> `
  --embed-provider OpenAI --embed-model <exact-model> `
  --bounded-run-authorization PATH\to\local-authorization.json
```

The compatibility alias `python -m proplex` shares the same flag. Without
`--bounded-run-authorization`, normal CLI behavior is unchanged: dotenv loading,
route defaults, retries/fallbacks, and ordinary persistence remain as before.

The authorization file is user-owned input for one run. It supplies routes,
limits, price facts, deadline, and `max_run_usd`. The repository does not
install bounded defaults, repository-owned prices, or reusable mode profiles.
Keep authorization files outside tracked source. Use fictional placeholders in
examples and tests only; do not commit executable live authorizations.

### Retired UI Entrypoint

Executing `python app.py` now prints a retirement notice and exits nonzero. It does not launch or redirect to another interface.

The retained [`ui/`](ui/) tree, saved-thread Streamlit follow-up code, and fixture-backed Streamlit demo are legacy prototype material. They are not current product usage paths and should not be repaired or extended as the basis of future UI architecture.

### CLI Model Environment

The public CLI configuration environment variables are:

```powershell
$env:SCRYRAVEN_FAST_PROVIDER = "OpenAI"
$env:SCRYRAVEN_FAST_MODEL = "gpt-5.4-mini"
$env:SCRYRAVEN_SMART_PROVIDER = "OpenAI"
$env:SCRYRAVEN_SMART_MODEL = "gpt-5.4"
$env:SCRYRAVEN_EMBED_PROVIDER = "OpenAI"
$env:SCRYRAVEN_EMBED_MODEL = "text-embedding-3-small"
$env:SCRYRAVEN_LOCAL_URL = "http://localhost:1234/v1"
```

Legacy `PROPLEX_*` aliases for those values remain temporarily supported as fallbacks. If both names are set, `SCRYRAVEN_*` wins.

## Developer Commands

Run tests:

```powershell
.\scripts\test.ps1
```

Run lint checks:

```powershell
.\scripts\lint.ps1
```

Run lint and tests together:

```powershell
.\scripts\check.ps1
```

Pass extra args to scripts:

```powershell
.\scripts\test.ps1 -q
.\scripts\lint.ps1 --fix
.\scripts\check.ps1 -q
```

## Retrieval Quality Habit

After changing routing, retrieval, provider, prompt, source-quality, citation, or answer-posture behavior, do not rely on vibes. Run focused tests first, then use bounded live validation only when it is explicitly needed.

For approved local review of existing run logs only, summarize them with:

```powershell
python scripts/aggregate_run_quality.py
```

Review local rows in `output/execution_log.jsonl`. Do not commit golden answers, raw transcripts, raw provider payloads, private traces, local packets, or comparison outputs.

The reference query list is a manual review aid, not a benchmark, scoring policy, or approval to run live queries.

## Secret Scanning Guardrail

This repo includes a lightweight pre-commit secret scan setup.

Install dev dependencies:

```powershell
pip install -r requirements-dev.txt
```

Install git hooks:

```powershell
pre-commit install
```

Run once on all files:

```powershell
pre-commit run --all-files
```

The secret scanner helps prevent committing API keys or other sensitive values. GitHub secret scanning and push protection should also be enabled for the public repository.

## Using the CLI

* Choose **Fast**, **Balanced**, or **Deep** with `--mode`
* Use `--academic` or `--news` to force those retrieval modes
* Use `--output` to write the report to a chosen file
* Use `--include-domains` or `--exclude-domains` to constrain source domains
* Run `python -m scryraven --help` for the complete option list

## Project Structure

* [`app.py`](app.py) — fail-closed tombstone for the retired legacy Streamlit entrypoint
* [`ui/`](ui/) — retained legacy Streamlit pages and helpers; reference/migration only
* [`core/`](core/) — pipeline orchestration, retrieval, prompts, source handling, and storage logic
* [`scryraven/`](scryraven/) — public CLI package
* [`proplex/`](proplex/) — legacy-compatible CLI package and compatibility surfaces
* [`scripts/`](scripts/) — quality aggregation, migrations, checks, and developer helpers
* [`docs/`](docs/) — architecture notes, validation notes, roadmap notes, and evaluation aids
* [`tests/`](tests/) — regression, contract, safety, and architecture tests
* [`output/`](output/) — local session history, passages cache, execution logs, review packets, and other generated artifacts; ignored by Git
* [`.env.example`](.env.example) — example environment variables

## Notes

* `.env`, local output artifacts, cache directories, and Python bytecode are git-ignored.
* The `proplex` package and `python -m proplex` remain as compatibility layers while public entrypoints use ScryRaven naming.
* Historical architecture and validation notes may mention older internal names.
* Streamlit remains in `requirements.txt` while retained legacy code and test/inspection consequences are evaluated for a later physical-cleanup phase.
* This project is a prototype. Expect rough edges.
