# Backend Deploy / 后端部署

## 中文优先

### 身份优先 / Identity first

本页主要面向 **backend 身份** 或 **both 身份中的 backend 阶段**。

- 如果当前机器是 `frontend`，不要优先按本页操作
- 先检查本地 `operator-identity.md`
- 若身份文档缺失，先补录身份，再继续部署

对 `both` 身份：
- 先完成 backend deploy / backend health
- 再进入 frontend 连接与 smoke

### Canonical commands

```bash
transcendence-memory backend deploy
transcendence-memory backend health
```

### 当前 runtime 对接口径

当前 operator 层文档对接的真实 backend runtime 是工作区内的私有仓库 `transcendence-memory-server/`。

在当前产品阶段，应把以下事实视为 canonical：
- 私有 HTTP runtime 入口由 `transcendence-memory-server/README.md` 定义
- 当前主链是 **LanceDB-only**，不是 PostgreSQL+pgvector 主链
- 当前私有服务默认监听 `127.0.0.1:8711`
- 私有部署链路口径为：`rag.zweiteng.tk` → Nginx → `127.0.0.1:8711` → `./scripts/run_task_rag_server.sh`
- 若 skill/operator 文档与 server 文档冲突，应先以 server runtime 真相为准，再回写 operator 文档

### Docker-first

未来公开分发可优先提供 Docker 路径，但当前仓库已拿到真实 proof 的私有部署入口仍以 `transcendence-memory-server/` 现有脚本链路为准。

若目标环境已有容器化封装，可继续检查：

```bash
docker compose ps
docker compose logs backend --tail=100
```

### Linux systemd

Linux 可使用：
- `deploy/systemd/transcendence-memory-backend.service`
- `deploy/systemd/transcendence-memory-backend.env.example`
- `deploy/systemd/README.md`

这些文件当前应被理解为 **公开分发阶段的 operator-facing wrapper / packaging assets**。

命名边界必须明确：
- **Eva 现网 live unit**：`rag-everything.service`
- **公开分发 wrapper 名**：`transcendence-memory-backend`

两者都指向同一条 canonical runtime 链路，但不是同一个 naming surface；不要把公开 wrapper 名写成 Eva 当前线上 unit 名。

常用检查：

```bash
systemctl status transcendence-memory-backend
journalctl -u transcendence-memory-backend -n 100 --no-pager
```

### Backend acceptance

至少确认：

```bash
curl -i http://127.0.0.1:8711/health
```

以及通过客户端或 curl 验证：
- `/search`
- `/embed`
- 如目标链路依赖 typed ingest，再验证 `/ingest-memory/objects`

### Failure order

优先排查：
1. 服务是否真的启动
2. 当前 operator 文档是否仍与 `transcendence-memory-server` runtime 真相一致
3. 环境变量 / provider / LanceDB runtime 是否可用
4. reverse proxy 或 advertised endpoint 是否正确
5. 日志里是否有 search/embed/ingest 运行时错误

## English

Use `backend deploy` and `backend health` as the canonical operator commands. At the current stage, the real runtime truth still lives in `transcendence-memory-server/`; public-safe Docker/systemd assets should be treated as operator-facing packaging surfaces unless they are proven against the active backend runtime.
