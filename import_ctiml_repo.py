"""
匯入 https://github.com/ctiml/convenience-store-data 的資料到本專案 SQLite
使用：
  python import_ctiml_repo.py /path/to/convenience-store-data --brands 7-11,familymart
未指定 --brands 時，預設只處理 7-11 與 familymart。
支援 .csv / .json / .geojson，多語欄位對應，避免重複（品牌+名稱+座標）。
"""
import os, sys, json, csv, sqlite3
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")

CSV_NAME_KEYS = ["name","store","storeName","NAME","店名","門市","門市名稱","門市名","POIName"]
CSV_ADDR_KEYS = ["address","addr","ADDRESS","Address","地址","地點","住址"]
CSV_LAT_KEYS  = ["lat","latitude","Latitude","LAT","y","Y","緯度","py"]
CSV_LNG_KEYS  = ["lng","lon","longitude","Longitude","LNG","x","X","經度","px"]



def coerce_float(v):
    try: return float(str(v).strip())
    except: return None

def pick(d, keys):
    for k in keys:
        if k in d and d[k] not in (None, ""): return d[k]
        for kk in d.keys():
            if kk.lower()==k.lower() and d[kk] not in (None,""): return d[kk]
    return None

def upsert_store(cur, name, address, lat, lng, brand):
    if not name or lat is None or lng is None: return False
    ex = cur.execute(
        "SELECT id FROM stores WHERE name=? AND printf('%.6f',latitude)=printf('%.6f',?) "
        "AND printf('%.6f',longitude)=printf('%.6f',?) AND IFNULL(brand,'')=IFNULL(?, '')",
        (name, lat, lng, brand)
    ).fetchone()
    if ex: return False
    cur.execute("INSERT INTO stores (name,address,latitude,longitude,brand) VALUES (?,?,?,?,?)",
                (name, address or "", float(lat), float(lng), brand))
    return True

def import_csv(cur, path, brand):
    added = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = pick(row, CSV_NAME_KEYS)
            addr = pick(row, CSV_ADDR_KEYS)
            lat  = coerce_float(pick(row, CSV_LAT_KEYS))
            lng  = coerce_float(pick(row, CSV_LNG_KEYS))
            if upsert_store(cur, name, addr, lat, lng, brand): added += 1
    return added

def import_json_like(cur, path, brand):
    added = 0
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # GeoJSON
    # 7-11 每縣市一檔的結構：{"city_id": "...", "city_name": "...", "stores": [ {...} ]}
    # 支援 {"city_name":"台中市","stores":[ {...}, {...} ]}
    if isinstance(data, dict) and isinstance(data.get("stores"), list):
        for row in data["stores"]:
            name = pick(row, CSV_NAME_KEYS)
            addr = pick(row, CSV_ADDR_KEYS)
            lat  = coerce_float(pick(row, CSV_LAT_KEYS))   # py
            lng  = coerce_float(pick(row, CSV_LNG_KEYS))   # px
            if upsert_store(cur, name, addr, lat, lng, brand):
                added += 1
        return added


    # List 或 Dict of lists
    seq = data if isinstance(data, list) else sum(([v] if isinstance(v, list) else [] for v in getattr(data, "values", lambda:[])()), [])
    if not seq and isinstance(data, dict): seq = []
    for row in (seq if seq else (data if isinstance(data, list) else [])):
        if not isinstance(row, dict): continue
        name = pick(row, CSV_NAME_KEYS); addr = pick(row, CSV_ADDR_KEYS)
        lat  = coerce_float(pick(row, CSV_LAT_KEYS)); lng  = coerce_float(pick(row, CSV_LNG_KEYS))
        if upsert_store(cur, name, addr, lat, lng, brand): added += 1
    return added

def main():
    if len(sys.argv) < 2:
        print("用法：python import_ctiml_repo.py /path/to/convenience-store-data [--brands 7-11,familymart]")
        sys.exit(1)
    base = Path(sys.argv[1]).expanduser().resolve()
    brands = ["7-11","familymart"]
    if "--brands" in sys.argv:
        i = sys.argv.index("--brands")
        if i+1 < len(sys.argv):
            brands = [b.strip() for b in sys.argv[i+1].split(",") if b.strip()]
    con = sqlite3.connect(DB_PATH); cur = con.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    # 確保 brand 欄位存在
    if "brand" not in [r[1] for r in cur.execute("PRAGMA table_info(stores)").fetchall()]:
        cur.execute("ALTER TABLE stores ADD COLUMN brand TEXT")
    total = 0
    for brand in brands:
        folder = base / brand
        if not folder.exists():
            print(f"[略過] 找不到資料夾：{folder}"); continue
        bname = "7-11" if "7" in brand else ("FamilyMart" if "family" in brand.lower() else brand)
        added_b = 0
        for p in folder.rglob("*"):
            if p.is_dir(): continue
            try:
                if p.suffix.lower()==".csv": added_b += import_csv(cur, p, bname)
                elif p.suffix.lower() in [".json",".geojson"]: added_b += import_json_like(cur, p, bname)
            except Exception: pass
        total += added_b
        print(f"{bname}: 新增 {added_b} 筆")
    con.commit(); con.close()
    print(f"總共新增：{total} 筆")

if __name__ == "__main__": main()
