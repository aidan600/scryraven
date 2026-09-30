# Catalog Table Integration 01

Status: offline integration of the previously selected Research catalog format.

## Provenance and decision

Catalog Table Representation Experiment 01 tested candidate `247a836`, restored
for Stage B at `3d9bcfb496d6e9adfa1dcce6bc3ddcdf2ec757e8`, against baseline
`b3aba7ee4be7ca8d4a7397103b8d7acc55f725a8`. The exact candidate patch,
reconstructed packets, hashes and adjudication are preserved as development
evidence under ignored `local-evals/runs/catalog-table-representation-01/`.

The original promotion result was **INCONCLUSIVE**: the required MD-80 default
confirmation shelved acquired cost estimates before Answer. Its valid IDs and
references showed no table parsing failure. The same retention-failure class
had occurred with object catalogs, so that observation did not attribute the
omission to the table representation. A later human/product architecture
decision selected the exact tested table format for ordinary production.

## Integrated format and scope

Research serializes `catalog.materials` and `catalog.candidates` as groups of
adjacent rows with the same sorted key set. Each group has full `columns` names
and positional `rows`; a key-set change begins another group. This preserves
row order, all values and unknown fields, including absent versus explicit
null. `AcquisitionLibrary.catalog()` still returns the logical object catalog.
The Research instruction adds only the tested two-line positional-mapping
explanation. There is no runtime format selector.

Evidence, Answer packets, schemas, attention, acquisition, providers, model
settings, retention and session persistence are unchanged. The Research
instruction-derived cache family changes; the stable packet breakpoint and
Answer cache family do not.

## Offline verification and limits

The accepted 35-state historical reconstruction inverts exactly: catalog
serialization fell from 429,717 to 306,161 characters (28.75%), and Research
packet serialization from 1,375,668 to 1,252,112 (8.98%). Counting the
163-character instruction once per call yields 8.57% packet reduction. The
historical clock fields are reconstruction proxies fixed identically on both
sides. Boundary tests cover key-set transitions, optional fields, nulls, empty
values, views, versions, navigation-only candidates and future fields.

This phase performed offline checks only: no live product, model, search, Read
or provider validation. Representation efficiency does not establish improved
Research judgment, stopping, retention, answer coverage or general reliability.
