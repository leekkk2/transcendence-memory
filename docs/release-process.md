# Release Process / 发布流程

## 中文优先

目标不是“自动发布一切”，而是让发布前检查足够明确、可重复、可拒绝不安全版本。

## 发布前必做 / Release Gates

### 1. 文档面完整

确认以下内容存在并同步：
- `README.md`
- `transcendence-memory/SKILL.md`
- `docs/backend-deploy.md`
- `docs/frontend-handoff.md`
- `docs/authentication.md`
- `docs/troubleshooting.md`
- `docs/release-compatibility.md`
- `docs/guide/HUMAN_GUIDE_INDEX.md`
- `docs/guide/INDEX.md`
- `docs/guide/installation.md`
- `docs/guide/backend-deployment.md`
- `docs/guide/frontend-handoff.md`
- `docs/guide/auth-handoff.md`

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

### 4. Public-safe surface

确认仓库中没有：
- 真实 API key
- 私有 endpoint
- 内部机器路径
- secret-bearing bundle 示例

### 5. Operator validation

发布前至少应完成一轮真实环境验证：
- backend deploy
- backend health
- frontend import / check / smoke
- `/health` / `/search` / `/embed`

## English

Before release:
1. confirm the skill and runbook surface is complete
2. validate `compat/release-compatibility.json`
3. run `ci.yml` and `release-checks.yml`
4. confirm the repository remains public-safe
5. perform at least one real operator validation pass
