# Migration Release Impact

## Purpose

This document explains how the `rag-everything-enhancer` migration state affects release claims for `transcendence-memory`.

## Preserved

- frontend/backend split
- builtin memory rule
- frontend config shape

## Adapted

- `container` namespace behavior is adapted rather than preserved exactly
- current backend implementation uses PostgreSQL + pgvector instead of the original LanceDB-centered service contract

## Not Migrated

- `build-manifest`
- `ingest-memory`
- private Eva-side deployment details

## Release Rule

Do not describe `transcendence-memory` as a full drop-in replacement for `rag-everything-enhancer` unless the adapted and not_migrated areas are explicitly disclosed.
