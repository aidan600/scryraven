# ScryRaven

ScryRaven is an approved research assistant for turning public-web research
questions into evidence-grounded answers.

## Repository state

This checkout is the small Part B foundation for a future walking skeleton.
The v1 application, runtime, and control-plane estate has been physically
removed from the active tree. Git history and the annotated tag
v1-final-implementation preserve the final v1 implementation baseline; there
is no active archive or fallback copy.

The walking skeleton is not implemented. In particular, this repository does
not yet implement Research, Analyst, Author, or their adaptive feedback flow.

## Retained foundation

- AGENTS.md, PRODUCT.md, and CURRENT.md are the current repository guidance.
- The minimal Cursor rule points contributors to those root files.
- scripts/run_brokered_command_once.py is the general operator doorman for
  credentialed local commands. It is not part of the product runtime.
- core/linkup_transport.py contains only mechanical Linkup standard discovery
  and direct Fetch donors.
- scryraven/ is a non-executable namespace foundation.
- tests/ contains focused offline tests for the doorman, the Linkup donors, and
  repository-local pytest hygiene.

The Linkup donors do not select providers, choose models, retry requests,
authorize work, track cost or tokens, custody evidence, judge support, or
write answers. Discovery material is returned as bounded navigation context;
Fetch material is returned with the selected URL that requested it.

## Local checks

Install the small runtime and development dependency sets:

    python -m pip install -r requirements.txt -r requirements-dev.txt

Run the focused offline suite:

    python -m pytest -q

Run lint and repository hooks:

    python -m ruff check .
    pre-commit run --all-files

These checks use mocked transports and do not make ScryRaven, provider, model,
search, or Fetch calls.

## Credentials

Copy .env.example to .env only when an operator needs to run a credentialed
local command through the doorman. Never commit .env, API keys, provider
payloads, private logs, caches, databases, or generated output.
