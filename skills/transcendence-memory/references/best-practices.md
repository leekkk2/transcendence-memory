# Best Practices

> Chinese version: [`best-practices.zh-CN.md`](./best-practices.zh-CN.md)

Field-tested usage patterns and anti-patterns for transcendence-memory. When `SKILL.md` and `troubleshooting.md` do not give a clear answer, this document is the authoritative reference.

---

## 1. The Two-Path Model: when to use `/search` vs `/query`

The server has **two completely independent data channels**. Content ingested through one channel is reachable only from that channel — there is no automatic bridge.

```
┌─────────────────────────────────────────────────┐
│           POST /ingest-memory/objects           │
│           POST /ingest-structured               │
│             (Lightweight Path)                  │
└────────────────────┬────────────────────────────┘
                     ↓
              LanceDB vector index
                     ↓
              POST /search
              (returns raw snippets + score)


┌─────────────────────────────────────────────────┐
│           POST /documents/text                  │
│           POST /documents/upload                │
│        (RAG-Anything Multimodal Path)           │
└────────────────────┬────────────────────────────┘
                     ↓
   entity extraction + relation inference + LLM
   indexing (asynchronous, 20–60s)
                     ↓
              Knowledge Graph
                     ↓
              POST /query
        (returns LLM-synthesized answer + citations)
```

### 1.1 Decision tree

| What you want | Ingest via | Retrieve via |
|---------------|-----------|--------------|
| Look up the original snippet / code / command | `/ingest-memory/objects` | `/search` |
| Get an LLM-synthesized answer across many memories | `/documents/text` | `/query` |
| Upload a PDF / image / Markdown file | `/documents/upload` | `/query` |
| Both of the above | **Dual-write** ↓ | `/search` or `/query` |

### 1.2 Dual-write pattern

When a piece of knowledge must support both verbatim lookup and LLM synthesis, write it twice:

```bash
# Path 1: structured object for /search
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","objects":[{"id":"recipe-1","title":"...","tags":[...],"text":"..."}],"auto_embed":true}'

# Path 2: long-form Markdown for the knowledge graph (used by /query)
DOC_TEXT=$(python3 -c "import json; print(json.dumps(open('/path/to/recipe.md').read()))")
curl -sS -X POST "${ENDPOINT}/documents/text" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d "{\"container\":\"${CONTAINER}\",\"text\":${DOC_TEXT},\"description\":\"...\"}"
# /documents/text enqueues and returns a job id (pid/job_id) immediately; the
# knowledge graph is built asynchronously in the background — do not block on
# it. The content simply becomes queryable a bit later. Use `/tm jobs` to check
# progress; a failed build is surfaced silently by the SessionStart hook.
```

> **Common false-positive** — going through Path 1 only makes `/search` succeed immediately, so it feels "done". Hours later `/query` returns "no relevant information in the knowledge base". This is not a bug; it is the intended path isolation.

---

## 2. Cross-project reuse: build a dedicated container per topic

### 2.1 Anti-pattern — dump everything into the default container

Most projects keep a generic default container (e.g. `my-project`, `home`) that accumulates thousands of conversation backups and notes. **A few high-quality memories written into such a container get drowned in the noise:**

- Observed: a 5,000+ chunk `my-project` container; 4 freshly written React Native OTA memories; query `"react native ota"` returned conversation backups for the entire `topk=10` window — none of the new memories surfaced
- Same 4 memories in a fresh `mobile-recipes` container (4 chunks total): top-1 score `0.475`, all four ranked in the top 4

### 2.2 Recommended — one dedicated container per reusable topic

For each cross-project, long-lived knowledge area, create a kebab-case container:

```
mobile-recipes      # RN field experience
ios-publishing-guides     # iOS release / review
flutter-recipes
auth-oidc-patterns
docker-prod-checklist
strapi-cms-patterns
```

### 2.3 Cross-container retrieval

Once content lives in a dedicated container, fetch it from any project with:

```bash
# Single dedicated container
/tm search --match mobile-recipes "react native ota"

# Fuzzy across all *-recipes containers
/tm search --match recipes "ota"

# Search every container
/tm search --all "react-native-ota-hot-update"
```

### 2.4 Dual-track embeddings + automatic union (v0.11.0+)

If your server runs **dual embedding tracks** (e.g. gemini-3072 primary + a sibling
`<container>_openai` mirror with text-embedding-3-small / 1024 dims), enable
`union_search_default: true` in `profiles.yaml`. Then a plain
`/tm search` against `my-container` will automatically query both tracks and merge
hits by `(taskId, chunkId)` dedup, giving you cross-track recall for free.

```yaml
# config/profiles.yaml
union_search_default: true
```

When triggered, the response carries `union_applied: true` and lists both
containers in `per_container_status`. If one track times out (default 3s), the
other still returns with `degraded: true` — the query never fully fails because
of a slow sibling.

To opt out per request (e.g. when you want a single-track baseline for an
eval):

```bash
/tm search "react native ota" --container my-container  # union as configured
curl ... -d '{"container":"my-container","query":"X","union":false}'  # force single
```

### 2.5 When to migrate

If a topic is being drowned in the default container, run a one-time migration:

1. `/tm search --match <oldcontainer> <topic>` with a large `topk` to dump candidates
2. Curate them into a JSONL file
3. `/tm batch <file>.jsonl --probe`, target the new container
4. Also push a curated Markdown digest through `/documents/text` to make the new container queryable

---

## 3. Indexing and async tasks: expected timings

| Operation | Container size | Expected duration |
|-----------|----------------|-------------------|
| `/ingest-memory/objects` write | any | < 1s |
| `/embed` synchronous, < 100 chunks | small | 5–30s |
| `/embed` synchronous, 100–1000 chunks | medium | 30–120s |
| `/embed` synchronous, 1000+ chunks | large | **avoid sync — use `background:true`** |
| `/documents/text` HTTP 200 returns | any | < 1s (only "accepted") |
| `/documents/text` queryable via `/query` | short doc | 20–40s |
| `/documents/text` queryable via `/query` | long doc (10KB+) | 1–3 minutes |

### 3.1 Do not synchronously embed a large container

Empirically, on multi-thousand-chunk containers `wait=true` produces no visible curl output even with `--max-time 240`, and exit code 0 is returned without a JSON body. **Switch to async** on any container above a few hundred chunks:

```bash
RESP=$(curl -sS -X POST "${ENDPOINT}/embed" \
  -H "X-API-KEY: ${API_KEY}" -H "Content-Type: application/json" \
  -d '{"container":"${CONTAINER}","background":true}')
PID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['pid'])")
echo "embed PID=$PID, polling..."
until ! curl -sS "${ENDPOINT}/jobs/${PID}" -H "X-API-KEY: ${API_KEY}" \
  | python3 -c "import json,sys; sys.exit(0 if json.load(sys.stdin).get('running') else 1)"; do
  sleep 5
done
```

### 3.2 `/documents/text` is async — do not block on the build

Server v0.15.0+ enqueues the build and returns a job id (`pid`) immediately; the
knowledge graph is built by a background worker. The content is **not instantly
queryable** — that is expected, not a bug. **Do not poll or sleep-wait**; just
let the build finish and the content becomes recallable in a later session.
Check progress with `/tm jobs`; a failed build is surfaced silently by the
SessionStart hook. (Old `< v0.15.0` servers build synchronously and may time
out — see `troubleshooting.md`.)

---

## 4. General checklist

### 4.1 Ingestion

- Concise tip / snippet (< 5 KB) → `/ingest-memory/objects` with `title` + `tags` for retrieval
- Long-form document (manual, design doc, API reference) → `/documents/text` or `/documents/upload`
- Bulk (50+ entries) → `/tm batch file.jsonl --probe --redact --resume`, then a single trailing `/embed`
- Contains secrets → use `--redact` or pre-filter manually
- Need both `/search` and `/query` → dual-write (see §1.2)

### 4.2 Retrieval

- Verbatim lookup → `/tm search "<query>"`; the lower the score, the closer the match (< 0.5 is typically a strong hit)
- Summary / answer → `/tm query "<question>"`; phrase the question **specifically** (entity names, library names)
- Cross-project recall → `/tm search --match <container-prefix> "<query>"`
- Container unknown → `/tm search --all "<query>"` with `topk=20` and browse hits

### 4.3 Container hygiene

- One topic per container (search experience is best below ~1000 chunks per container)
- Default containers (`my-project`, `home`, etc.) hold short-term project memory; long-lived reusable knowledge belongs in dedicated containers
- Periodically run `/tm containers` and prune obsolete containers via `DELETE /containers/{name}`

### 4.4 Configuration

- The default container in `~/.transcendence-memory/config.toml` is your "home" container; reach dedicated ones explicitly via `--match`, `containers[]`, or `container_pattern`
- For multi-machine setups, share configuration via `/tm connect <token>` rather than copying endpoint / api_key by hand

---

## 5. Real-world post-mortem: recent issues caught in the field

| Issue | Root cause | Fix / location |
|-------|-----------|----------------|
| `/query` returned "no information" after writing four OTA memories | Path isolation — only ingested via LanceDB, never into the knowledge graph | Dual-write through `/documents/text` → §1.2 |
| Newly written memories drowned in a 5,000+ chunk container | Low ranking under topk | Use a dedicated container → §2.2 |
| `/jobs/{pid}` polling never resolved (`status` field always None) | Real response uses `running`, not `status` | Corrected in `api-reference.md` |
| Synchronous `/embed` on a large container produced no curl output | Sync mode unsuitable at scale | Switch to `background:true` → §3.1 |
| Querying immediately after `/documents/text` returned "no information" | Knowledge graph build is asynchronous | Wait 20–60s → §3.2 |

When any of these patterns reappear, refer first to the updated `api-reference.md` / `troubleshooting.md`. New anti-patterns should be appended here.

---

## 6. Embedding/Reranker selection & dim decision tree (v0.7.0+)

### 6.1 Add a profile vs reuse default

| Situation | Recommendation |
|-----------|----------------|
| Single team/project, similar content per container | Use 1 default profile, don't over-split |
| Containers differ heavily (code vs CJK long-form vs multi-lang) | Split per topic, route via glob (`*_zh` / `*_code`) |
| Upstream quota frequently exhausted / unreliable | Add fallback chain (`embedding_fallbacks: [...]`, **same dim required**) |
| Want A/B comparison of retrieval quality | Dual-track naming (`home` + `home_openai`), use migrate tool to clone |
| Caller can't control container name | per-request `embedding_model` override |

### 6.2 Picking dim

```
What are you writing?
├─ Mixed-language long-form text → 3072 dim (gemini-embedding-001 / text-embedding-3-large)
│                                  Pros: high semantic fidelity, good cross-lingual alignment
│                                  Cost: ~3× LanceDB storage, p50 latency +30%
├─ Short snippets/code/tags → 1024 dim (text-embedding-3-small)
│                            Pros: low latency, small storage
│                            Cost: weaker recall for paraphrased semantics
└─ Long-tail multi-lang (JP/KR/AR) → multilingual-e5-large or jina-v3
```

### 6.3 Dim lock-in rule (HARD)

**The first write to a container locks its LanceDB vec column dim forever.** After:
- Same-dim profile swap → possible, but old/new vectors live in different semantic spaces — search quality becomes muddled
- Different-dim profile swap → **lance error: query dim X != column dim Y** immediately
- To change dim → use `scripts/migrate_embeddings.py` (in-place, auto-backup
  to `chunks_old_<ts>`) OR dual-track naming (new `<container>_openai` clone)

### 6.4 Dual-track naming convention

Mature projects run "main 3072 + mirror `*_openai` 1024" dual-write:

```bash
# Write (dual)
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" -H "X-API-KEY: ${API_KEY}" \
  -d '{"container":"home","objects":[...],"auto_embed":true}'
curl -sS -X POST "${ENDPOINT}/ingest-memory/objects" -H "X-API-KEY: ${API_KEY}" \
  -d '{"container":"home_openai","objects":[...],"auto_embed":true}'

# Retrieve (pick model)
curl -sS -X POST "${ENDPOINT}/search" -H "X-API-KEY: ${API_KEY}" \
  -d '{"container":"home","query":"..."}'           # 3072 high-fidelity
curl -sS -X POST "${ENDPOINT}/search" -H "X-API-KEY: ${API_KEY}" \
  -d '{"container":"home_openai","query":"..."}'    # 1024 low-latency
```

### 6.5 When to enable reranker

- **Default off**: routes `rerank.enabled: false`. Reranker doubles query latency (~+500ms)
- **Enable when**:
  - High document density (`/query` RAG retrieves top_k > 10, needs refinement)
  - Cross-lingual retrieval (rerankers beat pure vec on semantic alignment)
  - Business-critical search (users get stuck if results are off)
- **Per-request**: pass `"rerank": true` to `/search`/`/query`, no routes edit needed

---

## 7. Structured Memory Writing Conventions

The agent that retrieves a memory later uses **fuzzy natural-language phrases**,
not the original ASCII id. When writing a high-value memory, follow the three
layers below — recall hit-rate goes up dramatically.

### 7.1 Title with synonyms

> ❌ `[ASC + Play metadata fix @ project-a 1.0.1]`
> ✅ `[Submit / Release / Store-listing · store metadata fix @ 2026-05-26 project-a 1.0.1 lessons]`

Pack at least 2-3 synonyms into the title — verbs, entities, scene — so fuzzy
queries ("how do we submit?", "store rejection?") hit the same memory.

### 7.2 "When to recall me" line

Put a `When to recall me` line at the top of the body listing the recall
surface:

- **Verbs**: submit, release, rollback, ship, revert, 提审, 发版, 回滚
- **Entities**: app name, module name, subsystem (use placeholder names like
  `your-project` / `team-alpha`, do **not** leak real internal names)
- **Question shapes**: how do I…, what if it fails…, why does X happen…

This line doubles as a "semantic landmark" for your future self — if the agent
hits this line during search, it knows it landed on the right topic before
reading the body.

### 7.3 Bilingual redundant tags

Tag each memory with both technical ids and natural-language terms so both
retrieval paths hit:

```json
{
  "tags": ["asc", "release", "submit", "store-listing", "送审", "上架"]
}
```

Technical ids serve exact filters (`tag=release`); natural-language tags serve
fuzzy retrieval and human browsing.

---

## 8. High-Density Index Cards

For **SOPs, workflows, and decision trees that get re-asked repeatedly**,
create a dedicated "index card" memory that absorbs all the fuzzy-query
variants.

Properties:

- The card title carries every synonym someone might search for
- The body is a high-keyword-density entry point, linking to detailed memory
  ids / chunkIds
- The card absorbs fuzzy queries: once the agent hits it, it follows the links
  to the detail memories

Template:

```text
[Index Card · Deploy / Release / 部署 · full SOP]

When to recall me: deploy 部署 launch 发版 ship release pipeline ci/cd
rollback 回滚 port conflict docker compose

Steps:
1. ... (see mem-deploy-step1)
2. ... (see mem-deploy-step2)
...

Related memories: mem-deploy-step1, mem-deploy-rollback-sop, ...
```

Rule of thumb: build one index card per 50–100 same-topic memories — recall
quality has a clear inflection point there. Index cards do **not** replace
fine-grained memories; they are the "table of contents" for fuzzy searches.

---

## 9. Credential Redaction Checklist

Before writing a memory, verify the text does **not** contain:

- [ ] OpenAI / Anthropic / Stripe API keys (`sk-...`, `pk_live_...`,
      `sk_live_...`)
- [ ] Slack / GitHub tokens (`xoxb-...`, `xoxp-...`, `ghp_...`, `gho_...`)
- [ ] AWS access key id (`AKIA...`)
- [ ] `Authorization: Bearer <token>`, JWT triple-segment tokens
- [ ] URL-embedded `user:password` (e.g. `postgres://u:p@host`)
- [ ] PEM private-key blocks (`-----BEGIN ... PRIVATE KEY-----`)
- [ ] Plaintext secret values from `.env`

The PostToolUse + Stop hooks already pipe captured text through
`redact_secrets()` (see [`hooks/common.sh`](../../../hooks/common.sh)). But
**any programmatic bulk ingest must pipe explicitly** — otherwise secrets land
directly in the vector store.

Correct patterns:

```bash
# Use batch-ingest.py with --redact for bulk import
python3 scripts/batch-ingest.py "$ENDPOINT" "$API_KEY" "$CONTAINER" data.jsonl --redact

# In a custom script, source common.sh and pipe through redact_secrets
source hooks/common.sh
clean_text=$(printf '%s' "$raw_text" | redact_secrets)
```

If you discover secrets already in historical memories, run the
[`retrofit-playbook.md`](./retrofit-playbook.md) cleanup pass instead of
blindly overwriting the old container.
