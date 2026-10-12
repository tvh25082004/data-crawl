import json
import logging
import sys
import time

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("autohome")


def main():
    stages = sys.argv[1:] or ["index", "params", "images", "normalize", "excel"]
    t0 = time.time()

    if "index" in stages:
        log.info("=== STAGE 1: index ===")
        data = __import__("stage1_index").run()
        log.info("series total: %d", len(data["series"]))

    index = json.loads(config.INDEX_FILE.read_text())
    ids = [s["seriesid"] for s in index["series"]]

    limit = 0
    for a in sys.argv[1:]:
        if a.startswith("limit="):
            limit = int(a.split("=")[1])
    if limit:
        ids = ids[:limit]
        log.info("LIMIT applied: %d series", len(ids))

    if "params" in stages:
        log.info("=== STAGE 2: params ===")
        __import__("stage2_params").run(ids, workers=config.DEFAULT_WORKERS_PARAMS)

    if "images" in stages:
        log.info("=== STAGE 3: images ===")
        __import__("stage3_images").run(ids, workers=config.DEFAULT_WORKERS_IMAGES)

    if "normalize" in stages:
        log.info("=== STAGE 4: normalize ===")
        __import__("stage4_normalize").run()

    if "excel" in stages:
        log.info("=== STAGE 5: excel ===")
        __import__("export_excel").export()

    log.info("ALL DONE in %.0fs", time.time() - t0)


if __name__ == "__main__":
    main()
