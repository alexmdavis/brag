import io
import json
import pytest
from src.espn_client import fetch_json


def make_opener(payloads):
    """payloads: list of either bytes (success) or Exception (raise)."""
    calls = {"n": 0}

    def opener(request, timeout=0):
        i = calls["n"]
        calls["n"] += 1
        item = payloads[min(i, len(payloads) - 1)]
        if isinstance(item, Exception):
            raise item
        return io.BytesIO(item)

    return opener, calls


def test_returns_parsed_json():
    opener, _ = make_opener([json.dumps({"ok": 1}).encode()])
    assert fetch_json("http://x", opener=opener) == {"ok": 1}


def test_retries_then_succeeds():
    opener, calls = make_opener([OSError("flaky"), json.dumps({"ok": 2}).encode()])
    assert fetch_json("http://x", opener=opener, retries=3) == {"ok": 2}
    assert calls["n"] == 2


def test_raises_after_exhausting_retries():
    opener, _ = make_opener([OSError("down")])
    with pytest.raises(OSError):
        fetch_json("http://x", opener=opener, retries=2)
