# 🔌 Transcendence Memory Skill

> **Empowering AI Agents with Long-Term Memory.**

Transcendence Memory Skill 是连接 AI Agent (如 Claude, Gemini) 与 [transcendence-memory-server](../transcendence-memory-server/README.md) 的核心桥梁。它为 Agent 注入了“记住过去”和“找回上下文”的能力，解决长任务、跨会话中的“记忆碎片”问题。

---

## 🌟 为什么需要它？

普通的 AI 会话是易失的。本技能允许 Agent：
1. **记忆写回 (Write-back)**: 在任务结束或产生决策时，自动将关键信息持久化。
2. **状态恢复 (State Recovery)**: 在新会话开始时，通过检索快速同步上一个 Agent 的进度。
3. **跨项目索引**: 在 A 项目中产生的经验，可以被 B 项目的 Agent 检索利用。

---

## 🛠️ 安装与配置

### 1. 安装技能
```bash
# Claude Code 用户
/plugin install transcendence-memory
```

### 2. 连接服务端
安装后，直接在聊天框输入“初始化记忆连接”，Agent 会引导你输入从 [transcendence-memory-server](../transcendence-memory-server/README.md) 获取的 **Connection Token**。

---

## 🗣️ Agent 指令集 (示例)

当你激活本技能后，可以尝试以下指令：

- **“搜索关于 X 项目的最新架构决策”**: Agent 会调用底层 RAG 引擎进行语义搜索。
- **“记住这次部署失败的原因是端口冲突”**: Agent 会将此作为 `typed_object` 写入服务端。
- **“帮我生成任务交接总结并存入记忆”**: 自动提取当前任务状态并持久化。
- **“同步当前的 Container 索引”**: 强制触发服务端索引更新。

---

## 🏗️ 架构说明

本技能不存储任何本地数据，它是 [transcendence-memory-server](../transcendence-memory-server/README.md) 的无状态前端。
- **入口**: `skills/transcendence-memory/SKILL.md` (定义了 Agent 可理解的行为逻辑)。
- **配置**: 持久化在本地的 `config.toml`，仅包含 Endpoint 和 Token。

---

## 🔗 关联资源

- **服务端仓库**: [transcendence-memory-server](../transcendence-memory-server/README.md) —— 负责向量存储、RAG 计算和数据检索。
- **技能参考手册**: [Reference Docs](skills/transcendence-memory/references/api-reference.md)

---

## License
MIT
