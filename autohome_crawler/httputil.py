import json
import logging
import random
import threading
import time

import requests

log = logging.getLogger("autohome")

_UAS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; SM-S9180) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
]

_local = threading.local()


def _session():
    s = getattr(_local, "session", None)
    if s is None:
        s = requests.Session()
        s.mount("https://", requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30))
        s.mount("http://", requests.adapters.HTTPAdapter(pool_connections=30, pool_maxsize=30))
        _local.session = s
    return s


class BlockedError(Exception):
    pass


def fetch(url, referer=None, tries=6, timeout=(15, 45), accept_json=False):
    last = None
    for attempt in range(tries):
        headers = {
            "User-Agent": random.choice(_UAS),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "application/json, text/plain, */*" if accept_json else "*/*",
        }
        if referer:
            headers["Referer"] = referer
        try:
            resp = _session().get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                body = resp.content
                head = body.lstrip()[:64]
                if accept_json and (head[:1] == b"<" or b"\xe5\xae\x89\xe5\x85\xa8\xe9\xaa\x8c\xe8\xaf\x81" in body[:4000]):
                    raise BlockedError("waf challenge")
                if not accept_json and b"\xe5\xae\x89\xe5\x85\xa8\xe9\xaa\x8c\xe8\xaf\x81" in body[:4000]:
                    raise BlockedError("waf challenge")
                return body
            if resp.status_code in (403, 429, 500, 502, 503, 504):
                last = Exception(f"HTTP {resp.status_code}")
            else:
                last = Exception(f"HTTP {resp.status_code}")
        except BlockedError as e:
            last = e
        except Exception as e:
            last = e
        sleep = min(40.0, (1.2 * (2**attempt))) + random.uniform(0, 1.5)
        if isinstance(last, BlockedError):
            sleep = min(60.0, sleep * 1.8)
        log.debug("retry %s/%s %s err=%s sleep=%.1f", attempt + 1, tries, url[:100], last, sleep)
        time.sleep(sleep)
    raise RuntimeError(f"fetch failed after {tries}: {url[:160]} :: {last}")


def fetch_json(url, referer=None, tries=6):
    body = fetch(url, referer=referer, tries=tries, accept_json=True)
    return json.loads(body)
