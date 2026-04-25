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
# Wait ~30 seconds for the knowledge graph to finish building.
```

> **Common false-positive** — going through Path 1 only makes `/search` succeed immediately, so it feels "done". Hours later `/query` returns "no relevant information in the knowledge base". This is not a bug; it is the intended path isolation.

---

## 2. Cross-project reuse: build a dedicated container per topic

### 2.1 Anti-pattern — dump everything into the default container

Most projects keep a generic default container (e.g. `yzjx`, `imac`) that accumulates thousands of conversation backups and notes. **A few high-quality memories written into such a container get drowned in the noise:**

- Observed: a 5,000+ chunk `yzjx` container; 4 freshly written React Native OTA memories; query `"react native ota"` returned conversation backups for the entire `topk=10` window — none of the new memories surfaced
- Same 4 memories in a fresh `react-native-recipes` container (4 chunks total): top-1 score `0.475`, all four ranked in the top 4

### 2.2 Recommended — one dedicated container per reusable topic

For each cross-project, long-lived knowledge area, create a kebab-case container:

```
react-native-recipes      # RN field experience
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
/tm search --match react-native-recipes "react native ota"

# Fuzzy across all *-recipes containers
/tm search --match recipes "ota"

# Search every container
/tm search --all "react-native-ota-hot-update"
```

### 2.4 When to migrate

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

### 3.2 Do not query immediately after `/documents/text`

A 200 response only means the document has been queued. **Wait at least 30 seconds** before the first `/query`; long documents need longer. Inside scripts, use a sleep or a monitor loop.

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
- Default containers (`yzjx`, `imac`, etc.) hold short-term project memory; long-lived reusable knowledge belongs in dedicated containers
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
