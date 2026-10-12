import gzip
import json
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import config
import httputil

log = logging.getLogger("autohome")
_print_lock = threading.Lock()
_done = 0
_total = 0
_t0 = 0


def _progress(tag):
    global _done
    with _print_lock:
        _done += 1
        if _done % 50 == 0 or _done == _total:
            dt = time.time() - _t0
            rate = _done / dt if dt else 0
            eta = (_total - _done) / rate if rate else 0
            log.info("%s %d/%d (%.1f/s, eta %.0fs)", tag, _done, _total, rate, eta)


def param_path(sid: int) -> Path:
    return config.PARAMS_DIR / f"{sid}.json.gz"


def fetch_series_params(sid: int):
    path = param_path(sid)
    if path.exists() and path.stat().st_size > 50:
        return
    url = config.PARAM_URL.format(sid=sid)
    j = httputil.fetch_json(url, referer=config.PARAM_REFERER.format(sid=sid))
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False)
    _progress("params")


def run(series_ids, workers=config.DEFAULT_WORKERS_PARAMS):
    global _total, _t0
    todo = [sid for sid in series_ids if not (param_path(sid).exists() and param_path(sid).stat().st_size > 50)]
    log.info("params: %d todo / %d total", len(todo), len(series_ids))
    if not todo:
        return
    _total = len(todo)
    _done = 0
    _t0 = time.time()
    errors = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch_series_params, sid): sid for sid in todo}
        for fut in as_completed(futs):
            sid = futs[fut]
            try:
                fut.result()
            except Exception as e:
                errors.append(sid)
                log.warning("params fail %s: %s", sid, str(e)[:120])
    log.info("params done: %d errors", len(errors))
    if errors and len(errors) < len(todo):
        (config.PARAMS_DIR / "_failed.json").write_text(json.dumps(errors))
        log.info("retrying %d failed params...", len(errors))
        run(errors, workers=max(4, workers // 2))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    data = json.loads(config.INDEX_FILE.read_text())
    ids = [s["seriesid"] for s in data["series"]]
    if len(sys.argv) > 1:
        ids = ids[: int(sys.argv[1])]
    run(ids)
