"""Shared redaction contract 2026-09-09; generated CLI/server copies use this source.
Regex detection is defense in depth, not a guarantee that text contains no secrets.
"""
import json
import re
import sys
import os
from pathlib import Path

_PATTERNS = [
    (r'-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----[\s\S]*?(?:-----END (?:[A-Z]+ )*PRIVATE KEY-----|\Z)', '[REDACTED_PRIVATE_KEY]'),
    (r'\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|glpat-[A-Za-z0-9_-]{20,}|hf_[A-Za-z0-9]{30,})', '[REDACTED_TOKEN]'),
    (r'\b(?:sk_live_|pk_live_)[A-Za-z0-9]{10,}', '[REDACTED_TOKEN]'),
    (r'\bAIza[A-Za-z0-9_-]{35}', '[REDACTED_GOOGLE_KEY]'),
    (r'\bAKIA[A-Z0-9]{16}', '[REDACTED_AWS_KEY]'),
    (r'(?i)(Authorization:\s*Bearer\s+)[^\s"\x27,}]+', r'\1[REDACTED]'),
    (r'(?i)([a-z][a-z0-9+.-]*://)[^\s/@]*:[^\s/@]+@', r'\1[REDACTED]@'),
    (r'\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}', '[REDACTED_JWT]'),
    (r'(?im)(\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd)\b\s*[=:]\s*["\x27]?)(?!\[REDACTED)[^\s"\x27,}]+', r'\1[REDACTED]'),
]
_SECRET_KEYS = re.compile(r'(?i)^(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|passwd|private[_-]?key|authorization)$')


def redact_text(value: str) -> str:
    for pattern,replacement in _PATTERNS:
        value=re.sub(pattern,replacement,value)
    return value


def redact(value):
    if isinstance(value,str):return redact_text(value)
    if isinstance(value,list):return [redact(x) for x in value]
    if isinstance(value,dict):return {k:('[REDACTED]' if _SECRET_KEYS.fullmatch(str(k)) else redact(v)) for k,v in value.items()}
    return value


def preserve_private_memory():
    import tomllib
    path = Path(os.environ.get('TM_CONFIG', os.environ.get('TM_CONFIG_FILE', str(Path.home() / '.transcendence-memory/config.toml'))))
    try:
        config = tomllib.loads(path.read_text())
    except (OSError, ValueError):
        return False
    return config.get('privacy', {}).get('preserve_sensitive') is True


if __name__=='__main__':
    text=sys.stdin.read()
    if '--memory' in sys.argv and preserve_private_memory():sys.stdout.write(text)
    elif '--json' in sys.argv:sys.stdout.write(json.dumps(redact(json.loads(text)),ensure_ascii=False))
    else:sys.stdout.write(redact_text(text))
