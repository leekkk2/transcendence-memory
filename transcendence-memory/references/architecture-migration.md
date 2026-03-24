# Architecture Migration / 架构迁移说明

## Preserved

- frontend / backend split
- builtin memory remains enabled

## Adapted

- source backend was centered on LanceDB-oriented centralized service behavior
- current backend is centered on PostgreSQL + pgvector

## Not Migrated

- private Eva-only deployment assumptions
- exact LanceDB-per-container runtime parity
