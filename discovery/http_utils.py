from __future__ import annotations

import requests

DEFAULT_TIMEOUT = 25
DEFAULT_HEADERS = {
    "User-Agent": "car-prices-discovery/0.1 (+research; Python requests)",
    "Accept": "application/json",
}


def get_json_soft(url: str, **kwargs: object) -> tuple[dict | list | None, int, str | None]:
    """
    GET and parse JSON without raising. Returns (body|None, status, error).
    On non-JSON body, body is None and error may be set.
    """
    opts: dict = {"timeout": DEFAULT_TIMEOUT, "headers": DEFAULT_HEADERS}
    opts.update(kwargs)  # type: ignore[arg-type]
    try:
        r = requests.get(url, **opts)
    except requests.RequestException as e:
        return None, 0, str(e)
    try:
        data = r.json()
    except ValueError:
        return None, r.status_code, "response not json"
    return data, r.status_code, None
