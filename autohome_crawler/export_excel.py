import gzip
import json
import logging
import time

import xlsxwriter

import config
import translate_vi as tv

log = logging.getLogger("autohome")

IMG_COLS = [
    "seriesid", "brand", "manufacturer", "series", "picid",
    "classid", "classname", "specid", "specname", "imgurl", "width", "height",
]
IMG_WIDTHS = [10, 16, 22, 26, 12, 9, 16, 10, 34, 105, 8, 8]

# Số dòng ảnh tối đa mỗi workbook (~200MB nén, dưới hạn mức 250MB của SharePoint)
IMG_ROWS_PER_FILE = 3_000_000

HDR_VI = {
    "seriesid": "Mã dòng xe", "brand": "Hãng xe", "manufacturer": "Nhà sản xuất",
    "series": "Dòng xe", "picid": "Mã ảnh", "classid": "Mã loại ảnh",
    "classname": "Loại ảnh", "specid": "Mã biến thể", "specname": "Biến thể",
    "imgurl": "Đường dẫn ảnh", "width": "Rộng", "height": "Cao",
    "brand_id": "Mã hãng", "brand_logo": "Logo hãng", "series_count": "Số dòng xe",
    "price": "Giá (nghìn NDT)", "spec_count": "Số biến thể",
    "displacements": "Dung tích", "filter_columns": "Bộ lọc",
    "series_url": "Link trang xe", "gallery_url": "Link thư viện ảnh",
    "filter_type": "Loại bộ lọc", "filter_name": "Tên bộ lọc",
    "value": "Giá trị", "value_id": "Mã giá trị",
}
HDR_EN = {
    "seriesid": "Series ID", "brand": "Brand", "manufacturer": "Manufacturer",
    "series": "Series", "picid": "Pic ID", "classid": "Class ID",
    "classname": "Category", "specid": "Spec ID", "specname": "Variant",
    "imgurl": "Image URL", "width": "Width", "height": "Height",
    "brand_id": "Brand ID", "brand_logo": "Brand logo", "series_count": "Series count",
    "price": "Price (10k CNY)", "spec_count": "Spec count",
    "displacements": "Displacements", "filter_columns": "Filters",
    "series_url": "Series URL", "gallery_url": "Gallery URL",
    "filter_type": "Filter type", "filter_name": "Filter name",
    "value": "Value", "value_id": "Value ID",
}

SUMMARY_VI = [
    ("Nguồn dữ liệu", "https://www.autohome.com.cn/ (汽车之家)"),
    ("Thời điểm export", None),
    ("Ngôn ngữ dữ liệu", "Đã dịch Trung → Việt Nam (giá trị gốc còn sót nếu ngoài từ điển)"),
    ("Số hãng (brand)", None),
    ("Số nhà sản xuất", None),
    ("Số dòng xe (series)", None),
    ("Số dòng có giá niêm yết", None),
    ("Số xe con (biến thể) - sheet Specs", None),
    ("Số cột thông số/spec", None),
    ("Số dòng bộ lọc - sheet Filters", None),
    ("Tổng số ảnh - sheet Images_XX", None),
    ("Số sheet ảnh", None),
    ("Sheet Brands", "Hãng xe + logo + số dòng"),
    ("Sheet Manufacturers", "Nhà sản xuất theo hãng"),
    ("Sheet Series", "Dòng xe: giá, link, số biến thể, bộ lọc"),
    ("Sheet Specs", "1 dòng = 1 xe, cột = thông số kỹ thuật đã dịch"),
    ("Sheet Filters", "Giá trị bộ lọc: năm, dung tích, hộp số, tiêu chuẩn..."),
    ("Sheet Images_XX", "Toàn bộ ảnh CDN: loại ảnh, biến thể gắn kèm"),
    ("Ghi chú ● / ○", "● = Có (trang bị), ○ = Tuỳ chọn, '-' = Không"),
    ("Ghi chú file", "Dữ liệu ảnh được chia nhiều file *_images*.xlsx (<250MB) để upload SharePoint"),
]
SUMMARY_EN = [
    ("Source", "https://www.autohome.com.cn/ (Autohome)"),
    ("Export time", None),
    ("Language", "Data translated Chinese → English (untranslated terms kept as-is)"),
    ("Brands", None),
    ("Manufacturers", None),
    ("Series", None),
    ("Series with price", None),
    ("Specs rows - sheet Specs", None),
    ("Spec columns", None),
    ("Filter rows - sheet Filters", None),
    ("Total images - sheet Images_XX", None),
    ("Image sheets", None),
    ("Sheet Brands", "Brand + logo + series count"),
    ("Sheet Manufacturers", "Manufacturers by brand"),
    ("Sheet Series", "Series: price, links, specs, filters"),
    ("Sheet Specs", "1 row = 1 variant, columns = translated specs"),
    ("Sheet Filters", "Filter values: year, displacement, transmission..."),
    ("Sheet Images_XX", "All CDN images with category + variant"),
    ("Note ● / ○", "● = Yes (equipped), ○ = Optional, '-' = No"),
    ("File note", "Image data split across multiple *_images*.xlsx files (<250MB) for SharePoint upload"),
]


def _count_lines(path):
    n = 0
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for _ in f:
                n += 1
    except Exception:
        pass
    return n


def _precount():
    specs = _count_lines(config.SPECS_FILE)
    filters = _count_lines(config.FILTERS_FILE)
    series = _count_lines(config.SERIES_FILE)
    imgs = 0
    nfiles = 0
    for path in config.IMG_DIR.glob("*.jsonl.gz"):
        imgs += _count_lines(path)
        nfiles += 1
    return {"specs": specs, "filters": filters, "series": series,
            "images": imgs, "img_files": nfiles}


def _write_sparse(ws, r, values, fmt):
    """Ghi 1 dòng, BỎ QUA ô rỗng để file nhỏ hơn nhiều."""
    for ci, v in enumerate(values):
        if v is None or v == "":
            continue
        ws.write(r, ci, v, fmt)


def _make_formats(wb):
    return {
        "header": wb.add_format({"bold": True, "bg_color": "#DDEBF7", "border": 1,
                                 "text_wrap": True, "valign": "vcenter"}),
        "text": wb.add_format({"valign": "top"}),
        "title": wb.add_format({"bold": True, "font_size": 14}),
        "kv_k": wb.add_format({"bold": True, "bg_color": "#F2F2F2", "border": 1}),
        "kv_v": wb.add_format({"border": 1, "text_wrap": True}),
    }


def _export_tables(lang, counts, out_path):
    vi = lang == "vi"
    HDR = HDR_VI if vi else HDR_EN
    SUMMARY = SUMMARY_VI if vi else SUMMARY_EN
    clean = tv.clean_value

    index = json.loads(config.INDEX_FILE.read_text())
    columns = json.loads(config.COLUMNS_FILE.read_text())
    idx_by_id = {s["seriesid"]: s for s in index["series"]}

    ordered_cols = (
        [c for c in columns if c["kind"] == "meta"]
        + [c for c in columns if c["kind"] == "filter"]
        + [c for c in columns if c["kind"] not in ("meta", "filter")]
    )
    raw_names = [c["name"] for c in ordered_cols]
    translated = [tv.translate_column(n, lang) for n in raw_names]
    seen = {}
    final_names = []
    for n, raw in zip(translated, raw_names):
        if n in seen:
            seen[n] += 1
            n = f"{n} ({seen[n]})"
        else:
            seen[n] = 1
        final_names.append(n)
    n_spec_cols = len(final_names)
    n_img_sheets = max(1, (counts["images"] + config.SPECS_SHEET_MAX_ROWS - 1)
                       // config.SPECS_SHEET_MAX_ROWS)

    wb = xlsxwriter.Workbook(str(out_path),
                             {"constant_memory": True, "strings_to_urls": False})
    F = _make_formats(wb)

    # ---- Summary ----
    ws = wb.add_worksheet("Summary")
    ws.set_column(0, 0, 38)
    ws.set_column(1, 1, 95)
    title = ("Autohome.com.cn - Dữ liệu xe Trung Quốc (bản tiếng Việt)" if vi
             else "Autohome.com.cn - Full Crawl Dataset (English)")
    ws.write(0, 0, title, F["title"])
    vals = [
        time.strftime("%Y-%m-%d %H:%M:%S"),
        len(index["brands"]), len(index["manufacturers"]), len(index["series"]),
        sum(1 for s in index["series"] if s.get("price")),
        counts["specs"], n_spec_cols, counts["filters"], counts["images"], n_img_sheets,
    ]
    vi_iter = iter(vals)
    for i, (k, v) in enumerate(SUMMARY, start=2):
        ws.write(i, 0, k, F["kv_k"])
        ws.write(i, 1, next(vi_iter) if v is None else v, F["kv_v"])

    # ---- Brands ----
    ws = wb.add_worksheet("Brands")
    bheaders = ["brand_id", "brand", "brand_logo", "series_count"]
    ws.write_row(0, 0, [HDR.get(h, h) for h in bheaders], F["header"])
    ws.freeze_panes(1, 0)
    for i, w in enumerate([10, 22, 70, 12]):
        ws.set_column(i, i, w)
    counts_b = {}
    for s in index["series"]:
        counts_b[s["brand_id"]] = counts_b.get(s["brand_id"], 0) + 1
    for r, b in enumerate(index["brands"], start=1):
        ws.write_row(r, 0, [b["brand_id"], tv.translate_brand(b["brand"], lang),
                            b["brand_logo"], counts_b.get(b["brand_id"], 0)], F["text"])
    ws.autofilter(0, 0, len(index["brands"]), len(bheaders) - 1)

    # ---- Manufacturers ----
    ws = wb.add_worksheet("Manufacturers")
    ws.write_row(0, 0, [HDR.get(h, h) for h in ["brand_id", "brand", "manufacturer"]],
                 F["header"])
    ws.freeze_panes(1, 0)
    for i, w in enumerate([10, 22, 32]):
        ws.set_column(i, i, w)
    brand_name = {b["brand_id"]: b["brand"] for b in index["brands"]}
    for r, m in enumerate(index["manufacturers"], start=1):
        ws.write_row(r, 0, [m["brand_id"],
                            tv.translate_brand(brand_name.get(m["brand_id"], ""), lang),
                            tv.translate_brand(m["manufacturer"], lang)], F["text"])
    ws.autofilter(0, 0, len(index["manufacturers"]), 2)

    # ---- Series ----
    ws = wb.add_worksheet("Series")
    sheaders = [
        "seriesid", "brand", "manufacturer", "series", "price", "spec_count",
        "displacements", "filter_columns", "series_url", "gallery_url", "brand_logo",
    ]
    ws.write_row(0, 0, [HDR.get(h, h) for h in sheaders], F["header"])
    ws.freeze_panes(1, 0)
    for i, w in enumerate([10, 18, 24, 28, 18, 12, 30, 42, 45, 50, 70]):
        ws.set_column(i, i, w)
    r = 1
    with gzip.open(config.SERIES_FILE, "rt", encoding="utf-8") as f:
        for line in f:
            s = json.loads(line)
            row = []
            for h in sheaders:
                v = s.get(h, "")
                if h in ("brand", "manufacturer"):
                    v = tv.translate_brand(str(v), lang)
                elif h == "filter_columns" and v:
                    v = "、".join(
                        tv.translate_column(f"filter_{x}", lang)
                        for x in str(v).split("、") if x
                    ) if vi else v
                row.append(v)
            ws.write_row(r, 0, row, F["text"])
            r += 1
    ws.autofilter(0, 0, max(r - 1, 1), len(sheaders) - 1)
    log.info("Series sheet: %d rows", r - 1)

    # ---- Specs (wide, translated, bỏ ô rỗng) ----
    ws = wb.add_worksheet("Specs")
    ws.write_row(0, 0, final_names, F["header"])
    ws.freeze_panes(1, 6)
    for i, name in enumerate(final_names):
        if raw_names[i] in ("series_url", "brand_logo", "gallery_url"):
            w = 45
        elif raw_names[i] in ("brand", "series", "specname", "manufacturer"):
            w = 24
        elif raw_names[i].startswith("filter_"):
            w = 14
        else:
            w = 16
        ws.set_column(i, i, w)
    n_specs = 0
    r = 1
    with gzip.open(config.SPECS_FILE, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            outrow = []
            for raw in raw_names:
                v = row.get(raw, "")
                if raw in ("brand", "manufacturer"):
                    v = tv.translate_brand(str(v), lang) if v else ""
                elif isinstance(v, str) and v and raw not in ("series",):
                    v = clean(v, lang)
                outrow.append(v if v is not None else "")
            _write_sparse(ws, r, outrow, F["text"])
            r += 1
            n_specs += 1
    ws.autofilter(0, 0, max(n_specs, 1), n_spec_cols - 1)
    log.info("Specs sheet: %d rows x %d cols", n_specs, n_spec_cols)

    # ---- Filters ----
    ws = wb.add_worksheet("Filters")
    ws.write_row(0, 0, [HDR.get(h, h) for h in ["seriesid", "brand", "series",
                                                "filter_type", "filter_name",
                                                "value", "value_id"]], F["header"])
    ws.freeze_panes(1, 0)
    for i, w in enumerate([10, 18, 28, 16, 16, 20, 12]):
        ws.set_column(i, i, w)
    n_filters = 0
    r = 1
    with gzip.open(config.FILTERS_FILE, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            ftype = row["filter_type"]
            fname = row["filter_name"]
            val = row["value"]
            if vi:
                fname = tv.translate_column(f"filter_{ftype}", lang)
                val = clean(str(val), lang) if val else ""
            ws.write_row(r, 0, [row["seriesid"],
                                tv.translate_brand(row["brand"], lang),
                                row["series"], ftype, fname, val, row["value_id"]],
                         F["text"])
            r += 1
            n_filters += 1
    ws.autofilter(0, 0, max(n_filters, 1), 6)
    log.info("Filters sheet: %d rows", n_filters)

    wb.close()
    log.info("Tables done: %s (specs=%d, filters=%d)", out_path, n_specs, n_filters)
    return {"file": str(out_path), "specs": n_specs, "filters": n_filters}


def _export_images(lang, out_dir, counts):
    vi = lang == "vi"
    HDR = HDR_VI if vi else HDR_EN
    clean = tv.clean_value
    index = json.loads(config.INDEX_FILE.read_text())
    idx_by_id = {s["seriesid"]: s for s in index["series"]}
    img_files = sorted(config.IMG_DIR.glob("*.jsonl.gz"),
                       key=lambda p: int(p.stem.split(".")[0]))
    log.info("images: %d series files, expect %d rows", len(img_files), counts["images"])

    part = 0
    files = []
    wb = None
    ws = None
    r = 1
    rows_in_wb = 0
    sheet_no = 0
    total_imgs = 0

    def new_workbook():
        nonlocal wb, part, rows_in_wb
        if wb is not None:
            wb.close()
        part += 1
        rows_in_wb = 0
        path = out_dir / f"autohome_{lang}_{part:02d}_images.xlsx"
        files.append(str(path))
        wb = xlsxwriter.Workbook(str(path),
                                 {"constant_memory": True, "strings_to_urls": False})
        return wb

    def new_sheet():
        nonlocal ws, r, sheet_no
        sheet_no += 1
        ws = wb.add_worksheet(f"Images_{sheet_no:02d}")
        ws.write_row(0, 0, [HDR.get(c, c) for c in IMG_COLS], F["header"])
        ws.freeze_panes(1, 0)
        for i, w in enumerate(IMG_WIDTHS):
            ws.set_column(i, i, w)
        r = 1

    new_workbook()
    F = _make_formats(wb)
    new_sheet()

    for path in img_files:
        sid = int(path.stem.split(".")[0])
        base = idx_by_id.get(sid)
        if base is None:
            continue
        b = [tv.translate_brand(base["brand"], lang),
             tv.translate_brand(base["manufacturer"], lang), base["name"]]
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                try:
                    it = json.loads(line)
                except Exception:
                    continue
                if rows_in_wb >= IMG_ROWS_PER_FILE:
                    ws.autofilter(0, 0, max(r - 1, 1), len(IMG_COLS) - 1)
                    new_workbook()
                    F = _make_formats(wb)
                    new_sheet()
                elif r >= config.SPECS_SHEET_MAX_ROWS:
                    ws.autofilter(0, 0, r, len(IMG_COLS) - 1)
                    new_sheet()
                cls = tv.translate_imgclass(it.get("classname") or "", lang)
                spname = it.get("specname") or ""
                if spname:
                    spname = clean(spname, lang)
                _write_sparse(ws, r, [
                    it.get("seriesid"), b[0], b[1], b[2], it.get("picid"),
                    it.get("classid"), cls, it.get("specid"),
                    spname, it.get("imgurl"),
                    it.get("width"), it.get("height"),
                ], F["text"])
                r += 1
                rows_in_wb += 1
                total_imgs += 1
                if total_imgs % 1_000_000 == 0:
                    log.info("images written: %d (part %d, %.0fs)",
                             total_imgs, part, time.time() - t0)
    ws.autofilter(0, 0, max(r - 1, 1), len(IMG_COLS) - 1)
    wb.close()
    log.info("images done: %d rows, %d files", total_imgs, len(files))
    return files, total_imgs, sheet_no


def export(lang="vi"):
    global t0
    t0 = time.time()
    log.info("pre-counting rows...")
    counts = _precount()
    log.info("pre-count: %s", counts)

    tables_path = config.OUT_DIR / f"autohome_{lang}_01_tables.xlsx"
    tinfo = _export_tables(lang, counts, tables_path)
    img_files, total_imgs, n_img_sheets = _export_images(lang, config.OUT_DIR, counts)

    result = {
        "tables": tinfo["file"],
        "images": img_files,
        "specs": tinfo["specs"],
        "filters": tinfo["filters"],
        "images_rows": total_imgs,
        "image_sheets": n_img_sheets,
        "elapsed": round(time.time() - t0, 1),
    }
    log.info("Export done (%s): %s", lang, result)
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    import sys
    lang = sys.argv[1] if len(sys.argv) > 1 else "vi"
    export(lang)
