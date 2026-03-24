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

说明：
- `auth status` 是 redacted 输出
- refresh token 不应出现在 CLI 输出、bundle、或普通 config 中

### 人工验证

Phase 2 的 live OAuth / provider 验证仍需人工完成，见：
- `.planning/phases/02-authenticated-backend-core/02-VERIFICATION.md`

## English

Use API key or OAuth via the `auth` command group. Status output is intentionally redacted.
