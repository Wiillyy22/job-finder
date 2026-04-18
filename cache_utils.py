import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel

PROJECT_DIR = Path(__file__).parent
DEFAULT_CACHE_DIR = PROJECT_DIR / ".cache"


def build_cache_key(namespace: str, *parts: Any) -> str:
    payload = json.dumps(
        {
            "namespace": namespace,
            "parts": parts,
        },
        ensure_ascii=False,
        sort_keys=True,
        default=_json_default,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_json(
    namespace: str, key: str, cache_dir: Path | None = None
) -> Any | None:
    path = _cache_path(namespace, key, cache_dir)
    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def save_json(
    namespace: str,
    key: str,
    data: Any,
    cache_dir: Path | None = None,
) -> None:
    path = _cache_path(namespace, key, cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            default=_json_default,
        ),
        encoding="utf-8",
    )


def _cache_path(
    namespace: str, key: str, cache_dir: Path | None = None
) -> Path:
    base_dir = cache_dir or DEFAULT_CACHE_DIR
    return base_dir / namespace / f"{key}.json"


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
