# Backend Deploy / 后端部署

## 中文优先

### 当前仓库的职责

本仓库不再承载可独立运行的 backend 实现。
它负责的是：
- backend 部署说明
- backend 验收说明
- backend -> frontend handoff 交付说明
- operator 在 brand-new / isolated 环境中的引导文档

如果你需要当前真实 backend runtime，请按当前 canonical 口径使用私有 `transcendence-memory-server`。

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

### 当前 canonical runtime 口径

当前 operator 文档默认对接 `transcendence-memory-server/` 的真实 backend runtime。

当前默认私有服务端口径：
- `127.0.0.1:8711`
- LanceDB-only

若本仓库文档与 backend runtime 文档冲突，应以当前 backend runtime 真相为准，并回写本仓库文档。

### 部署前硬前置条件

在任何 brand-new / sandbox / isolated 环境里，先确认：

```bash
python3 --version
docker --version
docker compose version
```

并确认：
- Python 满足仓库要求（当前为 `>=3.13`）
- Docker / Docker Compose 可用
- 若依赖拉镜像或外部服务，网络/代理路径可用
- 当前会话是否能直接访问宿主机 Docker daemon

### Host Docker reminder

**通用默认路径** 仍然是 Docker-first：

```bash
docker compose ps
docker compose logs backend --tail=100
```

**设备/环境特定提醒：**
某些宿主机上，Docker 已安装，但当前会话可能不能直接访问 Docker daemon，需要改走宿主机 sudo Docker 路径，例如：

```bash
sudo docker compose ps
sudo docker compose logs backend --tail=100
```

这类 sudo 路径属于**当前设备/当前权限模型下的现实差异**，不应被当成所有环境的通用默认。

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

```bash
transcendence-memory backend export-connection --topology split_machine --output bundle.json
```

然后把 CLI 打印的 **Frontend handoff steps** 一并交给前端操作员，而不是只发 `bundle.json`。

### Backend acceptance

至少确认 backend 对外可达的 health 接口，并验证当前交付范围需要的业务路径。

最低要求：
- `GET /health`
- `POST /search`
- `POST /embed`
- 如目标链路依赖 typed ingest，再验证 `/ingest-memory/objects`

### Failure order

优先排查：
1. 当前说明是否仍与 canonical backend runtime 一致
2. 当前环境是否满足 Python / Docker / 网络等前置条件
3. 当前会话是否能直接访问宿主机 Docker daemon；若不能，再判断是否应改走宿主机 sudo Docker 路径
4. advertised endpoint 是否正确
5. handoff / auth / smoke 路径是否闭合

## English

This repository no longer carries an independently deployable backend implementation. It provides deployment-facing operator materials only: backend deployment guidance, acceptance expectations, and frontend handoff instructions. The current canonical backend runtime lives in `transcendence-memory-server`. Operators should treat `8711 + LanceDB-only` as the current runtime truth and use this repository as the skill/deployment/handoff documentation surface.