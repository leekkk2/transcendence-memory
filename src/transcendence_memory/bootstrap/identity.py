from __future__ import annotations

from .models import BootstrapSelection, ResolvedPaths, Role
from .paths import ensure_layout


def render_identity_document(selection: BootstrapSelection, paths: ResolvedPaths) -> str:
    role = selection.role
    topology = selection.topology.value
    transport_hint = selection.transport_hint.value

    if role == Role.FRONTEND:
        identity_summary = "本机身份是 frontend。你负责连接后端、校验联通性、补齐本地凭据，并验证 `health/search/embed`。"
        hard_boundary = "不负责部署本机后端；除非用户明确把本机身份改成 `backend` 或 `both`，否则不要把当前机器当成本地后端。"
        priorities = [
            "transcendence-memory/references/identity-frontend.md",
            "docs/frontend-handoff.md",
            "docs/authentication.md",
            "transcendence-memory/references/OPERATIONS.md",
        ]
    elif role == Role.BACKEND:
        identity_summary = "本机身份是 backend。你负责部署、健康检查、日志排查、导出连接信息，并维护后端可用性。"
        hard_boundary = "不应把当前机器默认当作 frontend 客户端使用面；优先关注部署、健康、排障和导出给前端的连接信息。"
        priorities = [
            "transcendence-memory/references/identity-backend.md",
            "docs/backend-deploy.md",
            "docs/troubleshooting.md",
            "transcendence-memory/references/OPERATIONS.md",
        ]
    else:
        identity_summary = "本机身份是 both。你同时负责 backend 和 frontend，但优先顺序应当是：先部署/确认 backend，再完成 frontend 连接与 smoke。"
        hard_boundary = "不要跳过 backend 直接把当前机器当作纯 frontend 使用；`both` 必须先完成后端可用性，再做前端验证。"
        priorities = [
            "transcendence-memory/references/identity-both.md",
            "docs/backend-deploy.md",
            "docs/frontend-handoff.md",
            "docs/troubleshooting.md",
        ]

    lines = [
        "# Operator Identity / 身份认知文档",
        "",
        "## 当前身份",
        f"- role: `{role.value}`",
        f"- topology: `{topology}`",
        f"- transport_hint: `{transport_hint}`",
        f"- config_root: `{paths.config_root}`",
        f"- secret_root: `{paths.secret_root}`",
        "",
        "## 核心规则",
        "- 在继续任何操作前，先按当前身份理解本机职责，再选择文档和命令。",
        "- 如果这份文档缺失、过期、或与现实不符，必须先补录/重建身份，再继续。",
        f"- {identity_summary}",
        f"- {hard_boundary}",
        "",
        "## 文档优先级",
        *[f"{idx}. `{doc}`" for idx, doc in enumerate(priorities, start=1)],
        "",
        "## 补录要求",
        "- 如果这是第一次使用、未正确初始化、或曾经意外退出，请先重新确认身份。",
        f"- 然后重新执行：`transcendence-memory init {role.value} --dry-run`",
        f"- 确认无误后执行：`transcendence-memory init {role.value} --yes`",
    ]
    return "\n".join(lines) + "\n"


def write_identity_document(selection: BootstrapSelection, paths: ResolvedPaths) -> None:
    ensure_layout(paths)
    paths.identity_file.write_text(
        render_identity_document(selection, paths),
        encoding="utf-8",
    )

