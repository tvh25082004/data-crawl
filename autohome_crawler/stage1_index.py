import json
import logging
import re

import config
import httputil

log = logging.getLogger("autohome")

LETTERS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

DL_RE = re.compile(r'<dl id="(\d+)"[^>]*>(.*?)</dl>', re.S)
DT_NAME_RE = re.compile(r'<dt>.*?<div><a[^>]*>([^<]+)</a>', re.S)
DT_LOGO_RE = re.compile(r'<dt>.*?<img[^>]*src="([^"]+)"', re.S)
MFG_RE = re.compile(
    r'class="h3-tit"><a[^>]*>([^<]+)</a></div>\s*<ul[^>]*>(.*?)</ul>', re.S
)
LI_RE = re.compile(r"<li id=['\"]s(\d+)['\"]>(.*?)</li>", re.S)
LI_NAME_RE = re.compile(r"<h4[^>]*><a[^>]*>([^<]+)</a></h4>")
LI_PRICE_RE = re.compile(r"指导价：<a[^>]*>([^<]*)</a>")


def parse_letter(html):
    rows = []
    for dl in DL_RE.finditer(html):
        block = dl.group(2)
        brand_id = int(dl.group(1))
        nm = DT_NAME_RE.search(dl.group(0))
        logo = DT_LOGO_RE.search(dl.group(0))
        brand = nm.group(1) if nm else ""
        logo_url = ("https:" + logo.group(1)) if logo and logo.group(1).startswith("//") else (
            logo.group(1) if logo else ""
        )
        for mfg in MFG_RE.finditer(block):
            manufacturer = mfg.group(1)
            for li in LI_RE.finditer(mfg.group(2)):
                body = li.group(2)
                name_m = LI_NAME_RE.search(body)
                price_m = LI_PRICE_RE.search(body)
                sid = int(li.group(1))
                rows.append(
                    {
                        "seriesid": sid,
                        "brand_id": brand_id,
                        "brand": brand,
                        "brand_logo": logo_url,
                        "manufacturer": manufacturer,
                        "name": name_m.group(1) if name_m else "",
                        "price": price_m.group(1) if price_m else "",
                        "series_url": f"https://www.autohome.com.cn/{sid}/",
                        "gallery_url": f"https://car.autohome.com.cn/pic/series/{sid}.html",
                    }
                )
    return rows


def run():
    if config.INDEX_FILE.exists():
        data = json.loads(config.INDEX_FILE.read_text())
        log.info("index exists: %d series", len(data["series"]))
        return data

    series_by_id = {}
    brands = {}
    mfgs = set()
    for letter in LETTERS:
        url = config.GRADE_URL.format(letter=letter)
        html = httputil.fetch(url, referer="https://www.autohome.com.cn/").decode("utf-8", "ignore")
        rows = parse_letter(html)
        log.info("letter %s: %d rows", letter, len(rows))
        for r in rows:
            sid = r["seriesid"]
            if sid not in series_by_id:
                series_by_id[sid] = r
            brands.setdefault(r["brand_id"], {"brand_id": r["brand_id"], "brand": r["brand"], "brand_logo": r["brand_logo"]})
            mfgs.add((r["brand_id"], r["manufacturer"]))

    series = sorted(series_by_id.values(), key=lambda x: x["seriesid"])
    brands_list = sorted(brands.values(), key=lambda x: x["brand_id"])
    data = {
        "brands": brands_list,
        "manufacturers": [{"brand_id": b, "manufacturer": m} for b, m in sorted(mfgs)],
        "series": series,
    }
    config.INDEX_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    log.info("index saved: %d brands, %d manufacturers, %d series",
             len(brands_list), len(mfgs), len(series))
    return data
