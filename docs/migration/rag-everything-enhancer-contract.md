# RAG-Everything Enhancer Migration Contract

## Purpose

This document records the sanitized source contract that `transcendence-memory` must preserve or explicitly account for when claiming compatibility with `rag-everything-enhancer`.

It does **not** copy private infrastructure or secrets. It captures the public-facing operator contract only.

## Source Intent

The original `rag-everything-enhancer` skill was designed as:

- a **frontend part** for OpenClaw client hosts
- a **backend part** for a centralized RAG service host
- an **enhancement layer** that keeps builtin memory enabled

Core rule:

- **builtin memory stays enabled**
- RAG is an enhancer, not a replacement

## Source Frontend Contract

The source frontend flow expected operators to configure:

- `endpoint`
- `auth.type`
- `auth.name`
- `auth.value`
- `defaultContainer`

The source env/setup flow also expected:

- `RAG_CONFIG_FILE`
- `RAG_ENDPOINT`
- `RAG_AUTH_HEADER`
- `RAG_API_KEY`
- `RAG_DEFAULT_CONTAINER`

The source auth header shape used `X-API-KEY`.

## Source Backend Contract

The source backend expected:

- a centralized service
- `/health` as an anonymous probe
- `/search` and `/embed` as authenticated endpoints
- operational acceptance only after `/health`, `/search`, and `/embed` all succeed

## Source Data and Namespace Semantics

The original skill documented a `container` namespace model:

- `imac`
- `eva`
- `aliyun`

and tied that model to a LanceDB-centered storage story.

## Migration Rule

`transcendence-memory` must do one of three things for each source behavior:

- **Preserved** — same essential operator expectation remains
- **Adapted** — behavior remains available, but with a different implementation or surface
- **Not Migrated** — behavior is not retained and must be called out explicitly

Silently dropping source behavior is not acceptable.

## Acceptance Rule

Migration compatibility is incomplete until the project clearly documents how `/health`, `/search`, and `/embed` verification maps to the current implementation.
