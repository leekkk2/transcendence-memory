# Release Process / 发布流程

## 中文优先

Phase 5 的目标不是“自动发布一切”，而是让发布前检查足够明确、可重复、可拒绝不安全发布。

## 发布前必做 / Release Gates

### 1. 人工验证 backlog

在正式对外发布前，至少要审阅并关闭这些阶段的人工验证项：

- Phase 2 — `.planning/phases/02-authenticated-backend-core/02-VERIFICATION.md`
- Phase 3 — `.planning/phases/03-cross-platform-deployment-and-health/03-VERIFICATION.md`
- Phase 4 — `.planning/phases/04-secure-connection-handoff-and-verification/04-VERIFICATION.md`

### 2. 兼容矩阵

确认：

- `compat/release-compatibility.json`
- `docs/release-compatibility.md`

中的 CLI / backend / skill / bundle 版本组合与当前发布目标一致。

### 3. CI / workflow

当前 workflow：

- `.github/workflows/ci.yml`
- `.github/workflows/release-checks.yml`

要求：

- 使用 full SHA pin 的 GitHub Actions
- 运行 pytest
- 校验 compatibility manifest
- 保持 release checks 显式化

### 4. 文档面

发布前确认这些文档存在且内容同步：

- `README.md`
- `docs/backend-deploy.md`
- `docs/frontend-handoff.md`
- `docs/authentication.md`
- `docs/troubleshooting.md`
- `docs/release-compatibility.md`

### 5. Skill 发布面

当前 `transcendence-memory` skill 已经发布到 `skills-hub`。如果后续版本升级：

- 更新 skill 内容
- 更新 `_meta.json` 版本
- 同步 `skills-hub` 索引和发布记录

## GitHub 安全建议 / GitHub Hardening Notes

- workflow 中第三方 action 必须 pin 到 full commit SHA
- 最终公开仓库应启用 GitHub 原生的 dependency review、secret scanning / push protection
- release pipeline 不应依赖未审核的浮动 action tag

## English

Before public release:

1. close or explicitly accept the human verification backlog from Phase 2 / Phase 3 / Phase 4
2. validate `compat/release-compatibility.json`
3. run `ci.yml` and `release-checks.yml`
4. confirm all bilingual docs are present and aligned
5. confirm the skill publication surface is in sync with the current repo state
