# D-prime Product Model-Route Config Boundary

Status: DPRIME-PRODUCT-MODEL-ROUTE-CONFIG-REPAIR-01 documentation guard.
Mode: REPAIR. No live model/provider/search/retrieval/fetch/read calls are
licensed or proved by this note.

Model-role features must consume provider/model selection and credential
initialization through the product's shared route/config boundary. The current
boundary is `core.product_model_route_config.initialize_product_model_route_config`,
with ordinary CLI model execution consuming it before product model validation.

D-prime may impose stricter execution policy, such as single-attempt,
no-fallback, and no-switching behavior, but must not create a separate provider
selector, credential loader, `.env` policy, or SDK lane unless a phase
explicitly licenses a new product model-route boundary.

D-prime must not create a separate provider selector or credential loader.

D-prime support assessment must use the product smart route as the provider/model
source: `RunConfig.smart_provider` / `RunConfig.smart_model`, CLI
`--smart-provider` / `--smart-model`, `product_model_role: smart`, and
`product_route_kind: smart_model_route`.

Retries and fallbacks are forbidden for D-prime support assessment until an
explicit attempt ledger exists that records each attempt, route, failure mode,
validation result, and final rollup policy.

Credential availability may be reported only as booleans such as
`OPENAI_API_KEY present in current process: true/false`. D-prime tooling must
not read, print, retain, or package raw `.env` contents, API keys, provider
payloads, raw prompts, raw model responses, private logs, DB/cache rows, or
unrelated output artifacts.

The allowed transport posture is: single-attempt audited product smart
transport. The product route/config boundary supplies model-role route and
credential initialization posture; the D-prime transport supplies only the
strict single approved provider/model attempt, SDK retries disabled, no fallback,
no provider switch, no raw payload retention, and safe blocker propagation.
