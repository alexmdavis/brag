import json
import urllib.request

_HEADERS = {"User-Agent": "Mozilla/5.0 (brag-board)"}


def _default_opener(request, timeout=30):
    return urllib.request.urlopen(request, timeout=timeout)


def fetch_json(url, opener=None, retries=3, timeout=30):
    """Fetch and parse JSON. Retries transient errors; raises the last error."""
    opener = opener or _default_opener
    request = urllib.request.Request(url, headers=_HEADERS)
    last = None
    for _ in range(max(1, retries)):
        try:
            with opener(request, timeout=timeout) as resp:
                return json.loads(resp.read())
        except Exception as exc:  # noqa: BLE001 - retry any transient failure
            last = exc
    raise last
