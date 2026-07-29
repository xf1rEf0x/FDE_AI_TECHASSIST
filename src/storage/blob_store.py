"""Shared JSON-blob persistence: Upstash Redis if configured, else local file.

Streamlit Community Cloud's filesystem is ephemeral (wiped on every reboot/
redeploy), so writing to local JSON files doesn't survive there. When
UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN are set (e.g. in
.streamlit/secrets.toml on Community Cloud), blobs persist to Upstash Redis
instead. Locally, with no Redis configured, behavior is unchanged.
"""

import json
import os
from pathlib import Path

_redis = None
_url = os.getenv("UPSTASH_REDIS_REST_URL")
_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
if _url and _token:
    from upstash_redis import Redis

    _redis = Redis(url=_url, token=_token)


def load_blob(key: str, path: str, default):
    """Load a JSON blob by Redis key, or from a local file if Redis isn't configured."""
    if _redis is not None:
        raw = _redis.get(key)
        return json.loads(raw) if raw else default
    p = Path(path)
    if not p.exists():
        return default
    with open(p) as f:
        return json.load(f)


def is_remote() -> bool:
    """True when Redis is configured and blobs persist remotely, not to a local file."""
    return _redis is not None


def save_blob(key: str, path: str, value) -> None:
    """Save a JSON blob by Redis key, or to a local file if Redis isn't configured."""
    if _redis is not None:
        _redis.set(key, json.dumps(value))
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(value, f, indent=2)
