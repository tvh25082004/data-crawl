import gzip
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import config
import httputil

log = logging.getLogger("autohome")
_lock = threading.Lock()
_done = 0
_total = 0
_t0 = 0
_stats = {"rows": 0, "pages": 0}


def _progress(tag, rows=0):
    global _done
    with _lock:
        _done += 1
        _stats["rows"] += rows
        if _done % 100 == 0 or _done == _total:
            dt = time.time() - _t0
            rate = _done / dt if dt else 0
            eta = (_total - _done) / rate if rate else 0
            log.info("%s %d/%d (%.2f/s, eta %.0fs, rows=%d)",
                     tag, _done, _total, rate, eta, _stats["rows"])


def img_path(sid: int) -> Path:
    return config.IMG_DIR / f"{sid}.jsonl.gz"


def chan_path(sid: int) -> Path:
    return config.IMG_CHAN_DIR / f"{sid}.json"


def _fetch_channel(sid: int) -> dict:
    path = chan_path(sid)
    if path.exists() and path.stat().st_size > 20:
        return json.loads(path.read_text())
    j = httputil.fetch_json(
        config.CHAN_URL.format(sid=sid),
        referer=config.PIC_REFERER.format(sid=sid),
    )
    path.write_text(json.dumps(j, ensure_ascii=False))
    return j


def fetch_series_images(sid: int):
    out = img_path(sid)
    if out.exists() and out.stat().st_size > 20:
        return 0
    tmp = out.with_suffix(".tmp.gz")
    if tmp.exists():
        tmp.unlink()
    chan = _fetch_channel(sid)
    result = chan.get("result") or {}
    categories = result.get("categorylist") or []
    cat_names = {c["id"]: c.get("name", "") for c in categories}
    total = sum(c.get("piccount", 0) for c in categories)
    rows = 0
    if total > 0:
        pages = (total + 499) // 500
        tmp = out.with_suffix(".tmp.gz")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            for page in range(1, pages + 1):
                url = config.PAGE_URL.format(sid=sid, page=page)
                j = httputil.fetch_json(url, referer=config.PIC_REFERER.format(sid=sid), tries=5)
                piclist = (j.get("result") or {}).get("piclist") or []
                for it in piclist:
                    row = {
                        "seriesid": sid,
                        "picid": it.get("id"),
                        "classid": it.get("typeid"),
                        "classname": cat_names.get(it.get("typeid"), ""),
                        "specid": it.get("specid"),
                        "specname": it.get("specname"),
                        "imgurl": it.get("imgurl"),
                        "width": it.get("width"),
                        "height": it.get("height"),
                    }
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    rows += 1
                with _lock:
                    _stats["pages"] += 1
                if len(piclist) < 500:
                    break
        tmp.rename(out)
    else:
        with gzip.open(out, "wt", encoding="utf-8") as f:
            pass
    return rows


def run(series_ids, workers=config.DEFAULT_WORKERS):
    global _total, _done, _t0
    todo = [sid for sid in series_ids if not (img_path(sid).exists() and img_path(sid).stat().st_size > 20)]
    log.info("images: %d todo / %d total", len(todo), len(series_ids))
    if not todo:
        return
    _total = len(todo)
    _done = 0
    _stats["rows"] = 0
    _stats["pages"] = 0
    _t0 = time.time()
    errors = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_series_images, sid): sid for sid in todo}
        for fut in as_completed(futs):
            sid = futs[fut]
            try:
                nrows = fut.result()
                _progress("images", rows=nrows)
            except Exception as e:
                errors.append(sid)
                log.warning("images fail %s: %s", sid, str(e)[:120])
    log.info("images done: %d errors, %d rows total", len(errors), _stats["rows"])
    if errors and len(errors) < len(todo):
        (config.IMG_DIR / "_failed.json").write_text(json.dumps(errors))
        log.info("retrying %d failed image series...", len(errors))
        run(errors, workers=max(4, workers // 2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    data = json.loads(config.INDEX_FILE.read_text())
    run([s["seriesid"] for s in data["series"]])
