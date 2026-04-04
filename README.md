# Transcendence Memory

自托管 Memory 增强技能 — 让 AI agent 连接、搜索、存储和管理云端记忆。

## 安装

```bash
# Claude Code Plugin
/plugin install transcendence-memory

# 或手动
git clone <repo-url> ~/.claude/skills/transcendence-memory
```

## 使用

安装后技能自动生效。当你提到记忆检索、RAG、embedding 等话题时，agent 会自动加载本技能。

首次使用时，agent 会引导你完成连接配置（只需一个 connection token）。

## 文件结构

```
.claude-plugin/                         # Claude Code 插件包装
skills/transcendence-memory/
  SKILL.md                              # 技能入口（日常使用）
  references/
    setup.md                            # 首次配置（仅首次加载）
    api-reference.md                    # API 完整参考
    ARCHITECTURE.md                     # 架构说明
    OPERATIONS.md                       # 操作验证
    troubleshooting.md                  # 排障
    templates/config.toml.template      # 配置模板
```

## 相关仓库

| 仓库 | 职责 |
|------|------|
| **transcendence-memory-server** | 后端服务：API、存储、索引、embedding |

## License

MIT
