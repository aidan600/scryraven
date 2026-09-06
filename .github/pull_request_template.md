# PR checklist

## Summary

What changed?

-

## Changed surfaces

- [ ] Root guidance or current truth
- [ ] Repository configuration or CI
- [ ] Operator doorman
- [ ] Linkup transport donor
- [ ] Focused offline tests
- [ ] Other:

## Validation

Commands run:

    python -m pytest -q
    python -m ruff check .
    pre-commit run --all-files

Results:

-

## Explicit non-changes

- [ ] No live ScryRaven, provider, model, search, or Fetch calls
- [ ] No secrets or private environment values exposed
- [ ] No walking-skeleton implementation
- [ ] No product runtime or executable entrypoint added

## Reviewer decision

What should the reviewer verify before merge?

-
