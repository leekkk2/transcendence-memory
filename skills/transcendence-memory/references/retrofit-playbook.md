# Memory Retrofit Playbook

> Optional reference. Load only when you need to retroactively improve the
> recall quality (or scrub credentials) of an existing memory container.

This playbook covers the "after-the-fact" case: a container has accumulated
thousands of memories that were written before the conventions in
[`best-practices.md`](./best-practices.md) §7–§9 were adopted. Naïve
overwriting destroys history; full LLM re-writes are too expensive. This SOP
documents the **append-not-overwrite** pattern that keeps the original record
intact while giving fuzzy queries a high-density entry point.

---

## 1. When to retrofit

Retrofit when **any** of these are true:

- Containers exceed ~1000 memories and recall hit-rate is degrading.
- The historical titles are ASCII-id heavy (`mem-asc-presubmit-abc123`,
  `recipe-2024-q3-fix`) with no natural-language synonyms.
- A credential leak is discovered — secret patterns already live in past
  ingested objects.
- The agent that consumes the memory has switched (e.g. new project, new
  language working pair) and the recall surface no longer matches the query
  vocabulary.

Do **not** retrofit if:

- The container is < 200 memories — just write new memories following §7–§9.
- The leak is one-off — surgical PUT to that single memory id is faster.
- You do not have a backup of the underlying JSONL or LanceDB table.

---

## 2. Scope decision — selective rather than full

A 6000-memory container does **not** need 6000 LLM rewrites. Empirically,
**8–12 high-density index cards + selective enrichment of the top 50 SOP
memories** covers ~80% of fuzzy queries. Plan accordingly:

| Layer | Effort | Coverage |
|-------|--------|----------|
| Build 8–12 index cards (one per major topic cluster) | Hours | Catches most fuzzy queries by absorbing them at the card |
| Append "When to recall me" headers to top 50 SOPs | Half a day | Lifts recall on the most-asked items |
| LLM-rewrite remaining long tail | Days+ | Diminishing returns |

The first two rows are the recommended scope. Only escalate to row 3 if
measured recall is still below target.

---

## 3. Workflow

### 3.1 Inventory

Pull `id + tags + first-line` for every memory in the container:

```bash
# Pseudocode — adapt to your storage backend
curl -sS "${ENDPOINT}/containers/${CONTAINER}/memories?fields=id,tags,head" \
  -H "X-API-KEY: ${API_KEY}" \
  -o inventory.jsonl
```

Cluster by regex on tags / first-line to identify 8–12 topic groups (deploy,
auth, paywall, release, debug-postmortem, …).

### 3.2 Append-only enrichment

For each memory you enrich, **do not overwrite**. Add new sections to the
top of the body:

```markdown
## 🔍 When to recall me
deploy 部署 launch 发版 release rollback 回滚 — "how do I redeploy after a
port conflict?"

## 📌 Core conclusion
<one-paragraph distilled answer>

## 📚 Original record
<verbatim original body — unchanged>
```

Update via the `PUT /containers/{c}/memories/{id}` endpoint:

```bash
curl -sS -X PUT "${ENDPOINT}/containers/${CONTAINER}/memories/${MEM_ID}" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}))' "$NEW_BODY")"

# Throttle: 200ms between calls to avoid hammering the embedding pipeline
sleep 0.2
```

### 3.3 Build index cards

For each topic cluster, create one new index-card memory following
[`best-practices.md`](./best-practices.md) §8. Link the card to the detail
memory ids you just enriched.

### 3.4 Rebuild the index

After all updates land, run one trailing embed:

```bash
curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"background\":true}"
```

The single background worker drains in order; duplicate `/embed` calls for the
same container coalesce.

---

## 4. Credential-leak retrofit

If the audit found memories containing real secrets:

1. **Take a backup first**. Export the container to JSONL.
2. Pipe each affected body through `redact_secrets()` (see
   [`hooks/common.sh`](../../../hooks/common.sh)).
3. PUT the redacted body back to the same memory id.
4. After all rewrites, run `/embed` once.
5. Rotate the leaked credentials at the source — redaction is mitigation, not
   remediation.

```bash
source hooks/common.sh

while IFS= read -r line; do
    id=$(printf '%s' "$line" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
    body=$(printf '%s' "$line" | python3 -c "import json,sys; print(json.load(sys.stdin)['text'])")
    clean=$(printf '%s' "$body" | redact_secrets)
    [ "$clean" = "$body" ] && continue   # nothing to do
    curl -sS -X PUT "${ENDPOINT}/containers/${CONTAINER}/memories/${id}" \
      -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
      -d "$(python3 -c 'import json,sys; print(json.dumps({"text": sys.argv[1]}))' "$clean")"
    sleep 0.2
done < inventory.jsonl
```

---

## 5. Rollback

If a retrofit batch goes wrong:

1. Stop further writes immediately.
2. Restore the container's LanceDB table from the pre-retrofit backup (or
   re-ingest from the exported JSONL).
3. Re-run `/embed` once.
4. Investigate before retrying — typically the cause is an over-eager
   regex in the enrichment step that mangled `## 📚 Original record`.

---

## 6. Non-goals

- This playbook does **not** delete original memories — the original body is
  preserved verbatim under `## 📚 Original record`.
- It does **not** require any external LLM rewrite service — all changes are
  template-based string concatenations.
- It does **not** replace the day-to-day conventions in
  [`best-practices.md`](./best-practices.md) §7–§9; it is a one-off cleanup
  pass to bring an old container up to the current convention.
