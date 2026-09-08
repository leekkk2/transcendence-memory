# Search and write contract (2026-09-09)

`/search` may rerank candidates according to its route or per-request `rerank`.
The server's result order is authoritative. Never re-sort mixed metrics.

| Field | Meaning |
|---|---|
| `score`, `vectorScore`, `vector_distance` | Squared L2 vector distance, **lower is better**. `vector_distance` is additive; old values are unchanged. |
| `distance_metric` | `l2_squared` for this server's explicit L2 execution path. Old servers may omit it. |
| `rerankScore`, `rerank_score` | Reranker relevance, **higher is better**; `null` if unavailable. May be raw logits; not a calibrated probability. |
| `rerank_applied` | Whether reranking actually ran; false is valid for vector-only retrieval. |
| `degraded`, `is_degraded` | Partial/unavailable components; inspect `message` and per-container status. |

Keep numeric zero. Fall back only when a same-metric field is missing/null:
```python
rerank = hit.get('rerank_score')
if rerank is None:
    rerank = hit.get('rerankScore')
```
Never replace a missing rerank score with vector distance, average the two, or
interpret 0.99 as 99% factual accuracy. Thresholds require a labeled evaluation set.

`score_threshold` remains a distance **upper bound**; positive values keep distance
<= threshold, and <=0 disables the gate. Native CLI/Bash `--max-distance` maps to
this existing parameter. A new independent rerank threshold is not enabled by default.

`/query` returns `answer` and `citations`; citations need not contain body text.
`top_score`, when present, is a distance, not answer confidence. Lite servers can
support search/ingest while declaring query/documents_text unsupported.

## Diagnostics

`GET /capabilities` reports a safe contract version, build revision (or null),
capability flags, and score semantics. `/health` exposes local readiness; it does
not run a paid upstream inference probe. Admin profile diagnostics distinguish
request alias, operator-declared resolved model, revision, and unknown identity.

## Write receipt

`accepted` means persisted, not indexed. New servers also return `object_ids`,
`index_job_id` (nullable), and `index_status`: queued / not_requested / unavailable.
A full queue can persist an object without scheduling its index; don't resend it.
`tm remember ... --verify` observes that job and original object, with a timeout.
A timeout does not authorize replay. Use `tm jobs <job_id>` and stored receipts.

## Dependencies and platforms

Bash wrappers require Bash, curl, jq; remember and redaction also require Python 3.
The native `transcendence-memory-cli` uses Python, httpx, Typer and Rich. It does not
require Bash/jq. PowerShell launchers forward a UTF-8 JSON argument array to it.
A bare skill install is not a lifecycle hook installation and never modifies agent
rules, hosts, DNS or global proxy settings by default.
