from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
INDEX_DIR = DATA / "index"
PARAMS_DIR = DATA / "params"
IMG_DIR = DATA / "images"
IMG_CHAN_DIR = IMG_DIR / "chan"
NORM_DIR = DATA / "norm"
OUT_DIR = ROOT / "output"

for d in (INDEX_DIR, PARAMS_DIR, IMG_DIR, IMG_CHAN_DIR, NORM_DIR, OUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

INDEX_FILE = INDEX_DIR / "series_index.json"
COLUMNS_FILE = NORM_DIR / "columns.json"
SPECS_FILE = NORM_DIR / "specs.jsonl.gz"
SERIES_FILE = NORM_DIR / "series_enriched.jsonl.gz"
FILTERS_FILE = NORM_DIR / "filters.jsonl.gz"

EXCEL_FILE = OUT_DIR / "autohome_full_data.xlsx"

GRADE_URL = "https://www.autohome.com.cn/grade/carhtml/{letter}.html"
PARAM_URL = "https://car-web-m.autohome.com.cn/car/param/getParamConf?site=1&seriesid={sid}"
CHAN_URL = (
    "https://car.m.autohome.com.cn/pic/getpicchannel"
    "?seriesid={sid}&specid=0&classid=1&colorid=0&innercolorid=0"
)
PAGE_URL = (
    "https://car.m.autohome.com.cn/pic/getpiclist"
    "?seriesid={sid}&specid=0&classid=0&colorid=0&innercolorid=0"
    "&pageindex={page}&pagesize=500"
)
PIC_REFERER = "https://car.m.autohome.com.cn/pic/series/{sid}.html"
PARAM_REFERER = "https://car.m.autohome.com.cn/config/series/{sid}.html"

SPECS_SHEET_MAX_ROWS = 1_048_000
DEFAULT_WORKERS_PARAMS = 16
DEFAULT_WORKERS_IMAGES = 24
DEFAULT_WORKERS = DEFAULT_WORKERS_IMAGES
