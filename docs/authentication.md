# Authentication / 认证说明

## 中文优先

### API Key

```bash
transcendence-memory auth set-api-key --api-key <your-key>
transcendence-memory auth status
```

### OAuth

```bash
transcendence-memory auth login --issuer <issuer> --authorize-url <url> --token-url <url> --client-id <id>
transcendence-memory auth status
transcendence-memory auth logout
```

### Safety rules

- `auth status` 必须是 redacted 输出
- refresh token 不应出现在 CLI 输出、bundle、普通 config、summary 中
- 切换 provider / auth 方案后，应重新做 `frontend check` / `frontend smoke`

## English

Use API key or OAuth through the `auth` command group. Status output must remain redacted and secret-safe.
