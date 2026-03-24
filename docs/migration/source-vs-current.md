# Source vs Current

## Preserved

- **builtin memory** remains enabled; the project still treats retrieval as an enhancement layer
- the product still has a **frontend/backend split**
- operators still verify behavior through `health`, `search`, and `embed`
- the project still uses a published skill package as an operator entry surface

## Adapted

- **Backend implementation**:
  - source: centralized LanceDB-oriented service
  - current: PostgreSQL + pgvector backend

- **Memory API semantics**:
  - source: request/response model centered on `container`
  - current: request/response model centered on generic `content` and `query`

- **Deployment surface**:
  - source: private Eva-side service/Nginx/service repair runbooks
  - current: Docker-first plus Linux `systemd` deployment assets

- **Skill role**:
  - source: private skill pack with direct frontend/backend rollout guidance
  - current: thin public skill with CLI-oriented guidance that now needs migration references

## Not Migrated

- original private endpoint values
- original real API key examples
- private host-specific operational details
- direct LanceDB-only backend implementation parity
- deprecated aliases such as `build-manifest` and `ingest-memory` are not currently implemented in the public codebase

## Concrete Semantic Difference

The most important migration difference is this:

- source contract: `/search` and `/embed` are `container`-scoped and aligned with LanceDB-per-container behavior
- current contract: `/api/v1/memory/search` and `/api/v1/memory/embed` use PostgreSQL + pgvector and no longer expose `container` as the primary request shape

That means `transcendence-memory` should not be described as a drop-in replacement unless a compatibility layer is added.

## Release Guidance

Any public release should reference this document before claiming migration compatibility.
