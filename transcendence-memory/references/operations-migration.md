# Operations Migration / 运维迁移说明

## Preserved

不要把 rollout 视为完成，除非：
1. `health` 成功
2. `search` 成功
3. `embed` 成功

## Adapted

当前项目的 deploy / health surface 已经迁移到：
- `backend deploy`
- `backend health`
- `frontend check`
- `frontend smoke`

## Important

HTTP 200 本身不等于成功。当前项目也沿用这个 operator expectation。
