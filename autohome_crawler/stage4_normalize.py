import gzip
import json
import logging
from collections import OrderedDict

import config

log = logging.getLogger("autohome")

META_COLS = [
    "seriesid",
    "brand",
    "manufacturer",
    "series",
    "specid",
    "specname",
    "year",
    "price",
    "price_yuan",
    "status",
    "series_url",
]

FILTER_TYPES = [
    "year", "displacement", "gearbox", "standards",
    "cartype", "drivemode", "seatcount",
]


def _flatten_value(mx: dict) -> str:
    v = (mx.get("value") or "").strip()
    if not v:
        ci = mx.get("colorinfo") or {}
        names = [c.get("name", "") for c in (ci.get("list") or [])]
        if names:
            v = "、".join(n for n in names if n)
    if not v:
        sub = mx.get("sublist") or []
        parts = []
        for s in sub:
            nm = s.get("name", "")
            val = (s.get("value") or "").strip()
            if val and val not in ("●", "○"):
                parts.append(f"{nm}:{val}")
            elif nm:
                parts.append(nm + (val if val else ""))
        v = "、".join(parts)
    if not v:
        v = (mx.get("subvalue") or "").strip()
    if not v and (mx.get("tip") or "").strip():
        v = (mx.get("tip") or "").strip()
    return v


def _load_series_index():
    data = json.loads(config.INDEX_FILE.read_text())
    return {s["seriesid"]: s for s in data["series"]}


def _iter_param_files():
    for path in sorted(config.PARAMS_DIR.glob("*.json.gz"), key=lambda p: int(p.stem.split(".")[0])):
        sid = int(path.stem.split(".")[0])
        try:
            with gzip.open(path, "rt", encoding="utf-8") as f:
                yield sid, json.load(f)
        except Exception as e:
            log.warning("bad param file %s: %s", path, str(e)[:80])


def run():
    idx = _load_series_index()
    columns = OrderedDict()
    for i, c in enumerate(META_COLS):
        columns[c] = {"name": c, "kind": "meta", "index": i}

    n_specs = 0
    n_filters = 0
    series_stats = {}

    f_specs = gzip.open(config.SPECS_FILE, "wt", encoding="utf-8")
    f_series = gzip.open(config.SERIES_FILE, "wt", encoding="utf-8")
    f_filters = gzip.open(config.FILTERS_FILE, "wt", encoding="utf-8")

    for n, (sid, payload) in enumerate(_iter_param_files(), 1):
        base = idx.get(sid)
        if base is None:
            continue
        result = payload.get("result") or {}
        specs = (result.get("specinfo") or {}).get("specitems") or []
        paramitems = result.get("paramitems") or []
        configitems = result.get("configitems") or []
        conditionlist = result.get("conditionlist") or []

        groups = paramitems + configitems
        spec_ids = [s.get("specid") for s in specs]

        row_map = {}
        for sp in specs:
            row = {
                "seriesid": sid,
                "brand": base["brand"],
                "manufacturer": base["manufacturer"],
                "series": base["name"],
                "specid": sp.get("specid"),
                "specname": sp.get("specname"),
                "year": sp.get("year"),
                "price": sp.get("minprice"),
                "price_yuan": sp.get("noshowprice"),
                "status": sp.get("specstatus"),
                "series_url": base["series_url"],
            }
            cond = sp.get("condition") or []
            for ci, cdef in enumerate(conditionlist):
                key = f"filter_{cdef.get('typevalue', ci)}"
                if ci < len(cond) and cond[ci]:
                    row[key] = cond[ci]
                    if key not in columns:
                        columns[key] = {
                            "name": key, "kind": "filter",
                            "group": "筛选条件", "itemtype": cdef.get("name"),
                            "index": len(columns),
                        }
            row_map[sp.get("specid")] = row

        for g in groups:
            gname = g.get("groupname") or ""
            iname = g.get("itemtype") or ""
            for item in g.get("items") or []:
                col = f"{gname}｜{item.get('name')}" if gname else item.get("name")
                if col in ("车型名称", "优惠信息"):
                    continue
                meta = columns.get(col)
                if meta is None:
                    meta = {"name": col, "kind": "param" if g in paramitems else "config",
                            "group": gname, "itemtype": iname, "index": len(columns)}
                    columns[col] = meta
                for mx in item.get("modelexcessids") or []:
                    row = row_map.get(mx.get("id"))
                    if row is None:
                        continue
                    val = _flatten_value(mx)
                    if val:
                        row[col] = val

        for sid_row, row in row_map.items():
            f_specs.write(json.dumps(row, ensure_ascii=False) + "\n")
            n_specs += 1

        scols = set()
        disp = set()
        for cdef in conditionlist:
            tval = cdef.get("typevalue")
            for v in cdef.get("list") or []:
                f_filters.write(json.dumps({
                    "seriesid": sid,
                    "series": base["name"],
                    "brand": base["brand"],
                    "filter_type": tval,
                    "filter_name": cdef.get("name"),
                    "value": v.get("name"),
                    "value_id": v.get("id"),
                }, ensure_ascii=False) + "\n")
                n_filters += 1
                scols.add(cdef.get("name"))
                disp.add(v.get("name"))

        srow = dict(base)
        srow["spec_count"] = len(specs)
        srow["filter_columns"] = "、".join(sorted(scols))
        srow["displacements"] = "、".join(sorted(x for x in disp if x and ("L" in x or "T" in x)))
        f_series.write(json.dumps(srow, ensure_ascii=False) + "\n")
        series_stats[sid] = len(specs)

        if n % 500 == 0:
            log.info("normalize %d series: %d specs, %d cols, %d filters",
                     n, n_specs, len(columns), n_filters)

    f_specs.close()
    f_series.close()
    f_filters.close()

    col_list = sorted(columns.values(), key=lambda x: x["index"])
    config.COLUMNS_FILE.write_text(json.dumps(col_list, ensure_ascii=False, indent=1))
    log.info("normalize done: %d specs rows, %d columns, %d filter rows",
             n_specs, len(col_list), n_filters)
    return {"specs": n_specs, "columns": len(col_list), "filters": n_filters}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
