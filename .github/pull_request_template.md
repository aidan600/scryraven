\# PR Checklist



\## Lane



\- \[ ] Fast Lane — docs / tests / UI-display / repo hygiene

\- \[ ] Review Lane — behavior-risk / safety / cost / product output



\## Summary



What changed?



\-



\## Changed surfaces



\- \[ ] Docs / README / comments

\- \[ ] GitHub template / repo metadata

\- \[ ] Tests only

\- \[ ] UI display only

\- \[ ] Local helper script

\- \[ ] Runtime code

\- \[ ] Retrieval / routing / provider selection / source filtering

\- \[ ] Prompts / Analyst / Economist / Author

\- \[ ] Telemetry / JSONL / SQLite / weak-corpus / follow-up behavior

\- \[ ] Other:



\## Behavior change?



\- \[ ] No production behavior change

\- \[ ] Behavior change



If behavior-changing, include Rule 0:



```text

failure\_analysis:

\- General failure class:

\- Blast radius:

\- Rules that apply:

\- Valid cases this could accidentally block or degrade:

\- Telemetry/diagnostics:

\- Simplest positive test:

\- Simplest negative-control test:

```



\## Validation



Commands run:



```text

```



Results:



```text

```



\## Explicit non-changes



\- \[ ] No live ProPlex queries

\- \[ ] No provider/model/search API calls

\- \[ ] No Streamlit run

\- \[ ] No Project Source changes unless explicitly approved

\- \[ ] No config/secrets/env/log/output/database changes

\- \[ ] No retrieval/routing/provider/prompt/Analyst/Economist/Author/telemetry/weak-corpus changes unless checked above



\## Reviewer questions



What should the reviewer decide, question, or double-check?



\-
