from __future__ import annotations

import uvicorn

from .app import app


def main() -> None:
    uvicorn.run("transcendence_memory.backend.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
