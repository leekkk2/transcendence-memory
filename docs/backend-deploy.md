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

**通用默认路径** 仍然是 Docker-first：

```bash
docker compose ps
docker compose logs backend --tail=100
```

如果目标环境已经有容器化封装，优先复用现有 Docker 能力，而不是额外发明新的部署方式。

**设备/环境特定提醒：**
某些宿主机上，Docker 虽然已安装，但当前会话可能不能直接访问 Docker daemon，需要改走宿主机的 sudo Docker 路径，例如：

```bash
sudo docker compose ps
sudo docker compose logs backend --tail=100
```

这类 sudo 路径属于**当前设备/当前权限模型下的现实差异**，不应被当成所有环境的通用默认。

适合：
- Linux
- macOS
- Windows（Docker Desktop）

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

### 部署后必须交给前端的信息

后端部署完成后，不能只告诉前端一个 backend URL。

至少应同时交付：
1. `bundle.json`（由 `backend export-connection --topology split_machine --output bundle.json` 生成）
2. 当前前端应使用的鉴权模式（如 `api_key` 或 `oauth`）
3. 前端仍需本地补齐的鉴权材料（例如 `api_key` / `oauth_login`）
4. 前端下一步应执行的命令顺序：
   - `transcendence-memory frontend import-connection --bundle-file bundle.json`
   - `transcendence-memory auth ...`（按当前 auth mode 补齐本地 auth）
   - `transcendence-memory frontend check`
   - `transcendence-memory frontend smoke`

推荐做法：
- 导出时使用：

```bash
transcendence-memory backend export-connection --topology split_machine --output bundle.json
```

- 然后把 CLI 在导出后打印的 **Frontend handoff steps** 一并发给前端操作员，而不是只发 `bundle.json`。

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
3. 当前环境是否能直接使用 Docker；若该设备的当前会话不能直接访问 Docker daemon，再判断是否应改走宿主机 sudo Docker 路径
4. 环境变量 / provider / LanceDB runtime 是否可用
5. reverse proxy 或 advertised endpoint 是否正确
6. 日志里是否有 search/embed/ingest 运行时错误

## English

Use `backend deploy` and `backend health` as the canonical operator commands. At the current stage, the real runtime truth still lives in `transcendence-memory-server/`; public-safe Docker/systemd assets should be treated as operator-facing packaging surfaces unless they are proven against the active backend runtime. After deployment, operators should hand off not only the redacted bundle but also the auth mode, the remaining local auth requirement, and the exact frontend next-step commands.