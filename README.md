# ScryRaven

ScryRaven is a weird little grounded-search lab for chasing claims, checking sources, and making answers show their receipts.

It is a source-grounded research assistant experiment backed by a Streamlit-free backend pipeline (`run_pipeline` in [`core/pipeline_orchestrator.py`](core/pipeline_orchestrator.py)). It:

* Routes query intent across web, news, and academic-style research flows
* Generates targeted search queries
* Retrieves sources from configured search providers
* Ranks and filters evidence
* Synthesizes cited reports
* Supports follow-up questions on saved research threads
* Experiments with source obligations, evidence sufficiency, and answer posture

The Streamlit shell lives under [`app.py`](app.py) and [`ui/`](ui/). Runtime artifacts and local logs are stored under [`output/`](output/), which is intentionally ignored by Git.

## Status

This repository is a cleaned public snapshot of a private research prototype. Some internal module names and historical validation notes may still reflect earlier working names. The public project name is now **ScryRaven**.

This is not a polished product. It is a working prototype and architecture lab for grounded answers, citation discipline, source-quality handling, and claim-aware retrieval.

## What It Does

When you click **Start Research**, the app:

1. Classifies your prompt
2. Plans search and retrieval work
3. Searches across one or more configured providers
4. Fetches and chunks source text
5. Scores evidence for relevance and source quality
6. Runs analysis and audit passes depending on mode
7. Renders a final markdown report with citations
8. Saves the session to local history for reopening and follow-up

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

Live Web UI, CLI, scripted Streamlit, provider/model, reference-query, and comparison runs may call external services. Treat them as approval-gated when working in review or validation mode.

### Web UI

```powershell
streamlit run app.py
```

Open the local URL shown in your terminal, usually:

```text
http://localhost:8501
```

### Headless CLI

```powershell
python -m scryraven "your query" --mode Balanced
```

The legacy compatibility entrypoint remains available:

```powershell
python -m proplex "your query" --mode Balanced
```

Use `python -m scryraven --help` for all CLI options. `python -m proplex --help` is preserved for existing scripts.

### Scripted Streamlit Launch

The app also supports scripted local launch through environment variables.

```powershell
$env:SCRYRAVEN_RUN_QUERY = "your query"
$env:SCRYRAVEN_RUN_MODE = "Balanced"
streamlit run app.py
```

Legacy `PROPLEX_RUN_QUERY` and `PROPLEX_RUN_MODE` aliases remain temporarily supported when the `SCRYRAVEN_*` names are absent.

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

## Using the App

* Enter a topic on the home screen and click **Start Research**
* Choose strategy in the sidebar:

  * **Fast**: quickest answer
  * **Balanced**: deeper synthesis
  * **Deep**: most thorough pipeline
* Use **Focus** mode for Web, Academic, or News-style research
* Open **Library** from the sidebar to search past threads
* On a thread, use **Export Markdown** to download the report
* Ask follow-up questions in chat on an open thread

Streamlit **Settings → Theme** light/dark support is supplemented by styles in [`ui/theme.py`](ui/theme.py).

## Project Structure

* [`app.py`](app.py) — Streamlit entrypoint
* [`ui/`](ui/) — Pages, sidebar, follow-up chat, and UI helpers
* [`core/`](core/) — Pipeline orchestration, retrieval, prompts, source handling, and storage logic
* [`scripts/`](scripts/) — Quality aggregation, migrations, checks, and developer helpers
* [`docs/`](docs/) — Architecture notes, validation notes, roadmap notes, and evaluation aids
* [`tests/`](tests/) — Regression, contract, safety, and architecture tests
* [`output/`](output/) — Local session history, passages cache, execution logs, review packets, and other generated artifacts; ignored by Git
* [`.env.example`](.env.example) — Example environment variables

## Notes

* `.env`, local output artifacts, cache directories, and Python bytecode are git-ignored.
* The `proplex` package and `python -m proplex` remain as compatibility layers while public entrypoints move to ScryRaven naming.
* Historical architecture and validation notes may mention older internal names.
* This project is a prototype. Expect rough edges.
