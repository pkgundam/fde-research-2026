import json
from pathlib import Path
import httpx
import pytest
from sources import base


def test_strip_html_unescapes_and_strips():
    s = "&lt;div&gt;&lt;h2&gt;About&lt;/h2&gt;&lt;p&gt;Hi &amp; bye&lt;/p&gt;&lt;/div&gt;"
    assert base.strip_html(s) == "About\nHi & bye"


def test_cached_get_writes_then_reads_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "RAW_DIR", tmp_path)
    calls = []

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, text='{"ok": 1}')

    monkeypatch.setattr(base, "_client", httpx.Client(transport=httpx.MockTransport(handler)))
    status, body = base.cached_get("https://x.test/a", "src/key1")
    assert (status, body) == (200, '{"ok": 1}')
    cached = json.loads((tmp_path / "src" / "key1.json").read_text())
    assert cached["status"] == 200 and cached["body"] == '{"ok": 1}' and "fetched_at" in cached

    status2, body2 = base.cached_get("https://x.test/a", "src/key1")
    assert (status2, body2) == (200, '{"ok": 1}')
    assert len(calls) == 1  # second call served from disk


def test_cached_get_caches_404(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "RAW_DIR", tmp_path)
    monkeypatch.setattr(base, "_client", httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404, text="nf"))))
    assert base.cached_get("https://x.test/b", "src/key2") == (404, "nf")
    assert (tmp_path / "src" / "key2.json").exists()
