# Release Compatibility / 版本兼容矩阵

## 中文优先

当前发布兼容矩阵定义在：

- `compat/release-compatibility.json`

核心字段：
- `cli_version`
- `backend_version`
- `skill_version`
- `bundle_version`

当前基线：
- CLI: `0.1.0`
- backend: `0.1.0`
- skill: `0.1.0`
- bundle: `1`

如果这些组合不匹配，发布检查应阻止发布。

## English

The machine-readable compatibility contract lives in `compat/release-compatibility.json` and defines the supported CLI/backend/skill/bundle combination.
