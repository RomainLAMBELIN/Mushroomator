"""HTTP helpers with retries and on-disk caching."""
import json
import time
from pathlib import Path

import requests

USER_AGENT = "Mushroomator/0.1 (projet personnel, https://github.com/RomainLAMBELIN/Mushroomator)"
_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT


class QuotaExceeded(RuntimeError):
    """The data provider's daily quota is used up: retrying today is pointless."""


def get(url, params=None, timeout=120, retries=5, **kwargs):
    last = None
    for attempt in range(retries):
        try:
            r = _session.get(url, params=params, timeout=timeout, **kwargs)
            if r.status_code == 429 and "Daily API request limit" in r.text:
                raise QuotaExceeded(r.json().get("reason", r.text))
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(min(60, 2 ** attempt * (5 if getattr(e.response, "status_code", 0) == 429 else 1)))
    raise last


def get_json(url, params=None, **kwargs):
    return get(url, params=params, **kwargs).json()


def download(url, dest, chunk=1 << 20):
    """Download `url` to `dest` once (skipped when the file already exists)."""
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with get(url, stream=True, timeout=600) as r, open(tmp, "wb") as f:
        for block in r.iter_content(chunk):
            f.write(block)
    tmp.replace(dest)
    return dest


def cached_json(path, producer):
    """Return the JSON stored at `path`, computing and saving it with `producer()` when missing."""
    path = Path(path)
    if path.exists():
        return json.loads(path.read_text())
    value = producer()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return value
