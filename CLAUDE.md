# Transcendence Memory — Agent Instructions

本仓库是一个 **跨平台 Agent 技能插件与客户端包装**；包含Bash/Python/PowerShell脚本和契约测试。

## 包含

- `skills/transcendence-memory/SKILL.md` — 技能入口
- `skills/transcendence-memory/references/` — 参考文档（按需加载）
- `.claude-plugin/` — 插件包装

## 不包含

- HTTP客户端核心 → 复用服务端仓库的 `cli-package`；不要新增第三套客户端
- 服务端代码 → `transcendence-memory-server`

## 编辑约束

- SKILL.md 不超过 500 行
- references/ 单文件不超过 300 行
- 所有示例使用占位符
- 服务端内容放 `transcendence-memory-server`

