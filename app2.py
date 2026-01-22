from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, g
import sqlite3, os, re
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from werkzeug.utils import secure_filename
from flask import send_from_directory
import csv, math
import json
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import random
import time
import threading
import numpy as np
from datetime import datetime, timedelta

'''
「WAL 解決的是讀寫並行問題，
但 SQLite 仍然只允許單一寫者，
因此在背景執行緒中仍需透過 Lock 將多個寫操作合併為單一 transaction，
以確保資料一致性與避免寫入競爭。」
'''
#確保「批次寫入庫存 + 通知」時資料一致，避免 race condition
DB_LOCK = threading.Lock()
#存貨參數設定
RESTOCK_TIMES = [
    (2, 45),    # 早上 9 點
    (14, 0),   # 下午 2 點
    (19, 0),   # 晚上 7 點
]
RESTOCK_QTY = 60       # 每次補貨固定數量
MAX_STOCK = 100        # 庫存上限
SAFETY_STOCK = 10      # 可選安全庫存（避免過度缺貨）

UPDATE_INTERVAL = 60   # 庫存更新間隔 (秒)
DEMAND_MIN = 0         # 隨機需求最小值
DEMAND_MAX = 3         # 隨機需求最大值

# 模擬參數
NUM_SIMULATIONS = 1000  # 蒙地卡羅模擬次數
SIMULATION_INTERVAL_MINUTES = UPDATE_INTERVAL / 60 # 模擬步進時間 (分鐘)





app = Flask(__name__)
app.url_map.strict_slashes = False
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-secret")
DB_PATH = os.path.join(os.path.dirname(__file__), "app.db")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'avatars')

#資料庫設計與穩定性（WAL + Lock）
def enable_wal_mode_robust():
    """使用獨立的連接強制啟用 Write-Ahead Logging (WAL) 模式。"""
    print("嘗試啟用 WAL 模式...")
    try:
        # 使用一個獨立連線，並設定較短的超時時間
        # 這樣可以盡快嘗試取得鎖定，並在成功後立即釋放
        con = sqlite3.connect(DB_PATH, timeout=2) 
        
        # 執行 PRAGMA
        con.execute("PRAGMA journal_mode = WAL;") 
        
        # 立即關閉並釋放連線
        con.close() 
        print("✅ WAL 模式已成功啟用。")
        
    except sqlite3.OperationalError as e:
        # 如果失敗，再次提示用戶檢查是否有其他程序正在使用
        print(f"❌ 無法啟用 WAL 模式: {e}。請確保沒有其他程式（如 SQLite 瀏覽器）開啟資料庫，並重新啟動伺服器。")
    except Exception as e:
        print(f"❌ 啟用 WAL 模式時發生未知錯誤: {e}")

#資料庫設計與穩定性（WAL + Lock）
# 在應用程式啟動時執行一次
# 請確保在 Flask 實例化之後，且在任何資料庫操作之前執行此函式。
enable_wal_mode_robust()

def _db_path():
    return os.path.join(os.path.dirname(__file__), "app.db")

def _accounts_password_col():
    """偵測 accounts 表要存哪個欄位：password_hash 或 password。"""
    try:
        con = sqlite3.connect(_db_path())
        cur = con.execute("PRAGMA table_info(accounts)")
        cols = {row[1] for row in cur.fetchall()}
    finally:
        con.close()
    if "password_hash" in cols:
        return "password_hash"
    elif "password" in cols:
        return "password"
    else:
        # 沒有密碼欄位就拋錯，避免悶錯
        raise RuntimeError("accounts 表缺少 password 或 password_hash 欄位")
    
def ensure_user_prefs_table():
    con = sqlite3.connect(_db_path())
    try:
        # 只保證表存在；不動你既有欄位（user_id, category, weight）
        con.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id   INTEGER NOT NULL REFERENCES accounts(id),
                category  TEXT    NOT NULL,
                weight    REAL    NOT NULL DEFAULT 1.0,
                PRIMARY KEY(user_id, category)         -- 複合主鍵，供 ON CONFLICT 使用
            );
        """)
        con.commit()
    finally:
        con.close()

#通知系統(低庫存or收藏商品特價)
# --- front_remaining_final integration: notifications schema helper (additive) ---
def __ensure_notifications_schema():
    import sqlite3, os
    db_path = os.path.join(os.path.dirname(__file__), "app.db")
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        # 先確保有最小結構（舊表也能套用；已存在不會覆蓋）
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.commit()

        # 讀現有欄位
        cur.execute("PRAGMA table_info(notifications)")
        have = {row[1] for row in cur.fetchall()}

        # 需要補的欄位
        adds = []
        if "product_id"   not in have: adds.append(("product_id",   "INTEGER"))
        if "product_name" not in have: adds.append(("product_name", "TEXT"))
        if "address"      not in have: adds.append(("address",      "TEXT"))
        if "latitude"     not in have: adds.append(("latitude",     "REAL"))
        if "longitude"    not in have: adds.append(("longitude",    "REAL"))

        # 逐一 ALTER TABLE 補欄位（存在就跳過）
        for col, typ in adds:
            try:
                cur.execute(f"ALTER TABLE notifications ADD COLUMN {col} {typ}")
            except Exception:
                pass

        con.commit()
    finally:
        try: con.close()
        except: pass

def user_has_prefs(user_id: int | None) -> bool:
    if not user_id:
        return False
    con = sqlite3.connect(_db_path())
    try:
        cur = con.execute("SELECT 1 FROM user_preferences WHERE user_id = ? LIMIT 1", (user_id,))
        return cur.fetchone() is not None
    finally:
        con.close()

# --- 儲存/更新使用者偏好 ---
def save_user_prefs(user_id: int, categories: list[str]):
    """把這次勾選的品類存進去：沒勾到的刪除、勾到的逐筆 UPSERT。"""
    ensure_user_prefs_table()
    cats = [str(x) for x in categories]

    con = sqlite3.connect(_db_path())
    try:
        con.execute("PRAGMA foreign_keys = ON")

        # 先刪掉「這次沒有勾選」的
        if cats:
            ph = ",".join("?" * len(cats))
            con.execute(
                f"DELETE FROM user_preferences WHERE user_id = ? AND category NOT IN ({ph})",
                (user_id, *cats)
            )
        else:
            con.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))

        # 逐筆 UPSERT 到 (user_id, category)
        for cat in cats:
            con.execute("""
                INSERT INTO user_preferences (user_id, category, weight)
                VALUES (?, ?, 1.0)
                ON CONFLICT(user_id, category) DO UPDATE SET
                  weight = excluded.weight
            """, (user_id, cat))

        con.commit()
    finally:
        con.close()
        
def ensure_schema():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    # stores.brand
    cur.execute("PRAGMA table_info(stores)"); cols=[r[1] for r in cur.fetchall()]
    if "brand" not in cols:
        try: cur.execute("ALTER TABLE stores ADD COLUMN brand TEXT")
        except: pass
    # products.category
    cur.execute("PRAGMA table_info(products)"); pcols=[r[1] for r in cur.fetchall()]
    if "category" not in pcols:
        try: cur.execute("ALTER TABLE products ADD COLUMN category TEXT")
        except: pass
    # preferences
    cur.execute("""CREATE TABLE IF NOT EXISTS user_preferences(
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        weight REAL NOT NULL DEFAULT 1.0,
        PRIMARY KEY (user_id, category),
        FOREIGN KEY (user_id) REFERENCES accounts(id) ON DELETE CASCADE
    )""")
    # reviews
    cur.execute("""CREATE TABLE IF NOT EXISTS product_reviews(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES accounts(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
    )""")
    # ads
    cur.execute("""CREATE TABLE IF NOT EXISTS ads(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_url TEXT NOT NULL,
        link_url TEXT,
        is_active INTEGER NOT NULL DEFAULT 1
    )""")
    con.commit(); con.close()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*(math.sin(dlon/2)**2)
    c = 2 * math.asin(min(1, math.sqrt(a)))
    return R * c

#背景庫存模擬系統（核心特色）
# 啟動庫存更新的背景執行緒，啟動一個常駐背景執行緒，不依賴使用者請求。
def start_background_tasks():
    # 設置 daemon=True 確保主程序結束時，這個執行緒也會結束
    thread = threading.Thread(target=update_stock, daemon=True)
    thread.start()
    print("[INFO] Background stock update thread started.")

# 新增通知冷卻時間 (秒)，例如 4 小時
NOTIFICATION_COOLDOWN = 60 * 60 * 4
# 用於防止重複通知的快取和鎖定
notification_cache = {}
cache_lock = threading.Lock()

#庫存引擎
def update_stock():
    while True:
        time.sleep(UPDATE_INTERVAL) #每 UPDATE_INTERVAL 秒執行一次
        now = datetime.now()

        # 為了避免長時間持有 DB_LOCK，先在外部計算好所有更新
        products_to_update = []
        notifications_to_add = []
        
        try:
            # 讀取產品清單（不加鎖）
            conn = sqlite3.connect(DB_PATH, timeout=0.5)
            cursor = conn.cursor()
            cursor.execute("SELECT id, remaining_qty, name FROM products")
            products = cursor.fetchall()
            conn.close()
        except Exception as e:
            print(f"[ERROR] 讀取產品清單失敗: {e}")
            continue

        # 計算補貨和消耗
        for pid, qty, name in products:
            new_qty = qty
            
            # 補貨檢查
            for rh, rm in RESTOCK_TIMES:
                if now.hour == rh and now.minute == rm:
                    new_qty = min(qty + RESTOCK_QTY, MAX_STOCK)
                    if new_qty != qty:
                         print(f"[補貨] 商品 {pid} 補貨 {new_qty - qty} 件，庫存 = {new_qty} (預計)")

            # 消耗檢查
            demand = random.randint(DEMAND_MIN, DEMAND_MAX)
            # 如果補貨沒有發生，就使用原始的 qty 來計算消耗，避免重複計算
            base_qty = new_qty if new_qty != qty else qty 
            final_qty = max(0, base_qty - demand)

            # 準備更新
            if final_qty != qty:
                products_to_update.append((final_qty, pid))
                print(f"[消耗] 商品 {pid} 消耗 {base_qty - final_qty} 件，庫存 = {final_qty} (預計)")

            # 低庫存通知（使用最終庫存判斷）
            if final_qty > 0 and final_qty <= SAFETY_STOCK and qty > SAFETY_STOCK:
                msg = f"注意！商品「{name}」庫存已低於安全庫存 ({SAFETY_STOCK}件)，目前剩餘 {final_qty} 件。"
                notifications_to_add.append((0, msg, pid))

        # **STEP 3: 在一個單一事務中寫入所有資料** 一次 transaction 寫回 DB
        if products_to_update or notifications_to_add:
            with DB_LOCK:
                try:
                    conn = sqlite3.connect(DB_PATH, timeout=5.0) # 增加 timeout
                    cur = conn.cursor()

                    # 批量更新庫存
                    cur.executemany("UPDATE products SET remaining_qty=? WHERE id=?", products_to_update)
                    
                    # 批量新增通知
                    cur.executemany(
                        "INSERT INTO notifications (user_id, message, product_id) VALUES (?,?,?)",
                        notifications_to_add
                    )

                    conn.commit()
                    print(f"[INFO] 本次批次更新完成。產品數:{len(products_to_update)}，通知數:{len(notifications_to_add)}")
                except Exception as e:
                    # **請將此處修改成更詳細的輸出**
                    import traceback
                    print(f"[FATAL ERROR] 批次寫入失敗: {e}")
                    traceback.print_exc() # 輸出完整的錯誤堆疊，幫助偵錯
                    # 確保發生錯誤時資料庫回滾，保持一致性
                    try: conn.rollback() 
                    except: pass
                finally:
                    try: conn.close()
                    except: pass
'''#蒙地卡羅售罄預測（學術亮點），預測商品「大約幾小時後賣完」
def _forecast_stock(pid):
    """
    根據蒙地卡羅模擬預測商品售罄時間 (小時)。
    
    Return:
      > 0: 預計售罄時間 (小時), 
      = 0: 庫存已為 0, 
      < 0: 預測失敗或商品不存在 (-1)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. 取得當前庫存
    cursor.execute("SELECT remaining_qty FROM products WHERE id=?", (pid,))
    product_row = cursor.fetchone()
    conn.close()

    if not product_row:
        return -1  # 商品不存在

    current_stock = product_row["remaining_qty"]

    # 2. 庫存為 0，回傳 0
    if current_stock == 0:
        return 0

    # 3. 蒙地卡羅模擬
    sell_out_times_minutes = []
    MAX_SIMULATION_MINUTES = 48 * 60 # 最長模擬 48 小時
    
    for _ in range(NUM_SIMULATIONS):
        sim_stock = current_stock
        time_elapsed_minutes = 0
        
        while sim_stock > 0 and time_elapsed_minutes < MAX_SIMULATION_MINUTES:
            # 每個時間間隔內的隨機需求
            demand = random.randint(DEMAND_MIN, DEMAND_MAX)
            
            sim_stock -= demand
            time_elapsed_minutes += SIMULATION_INTERVAL_MINUTES
        
        if sim_stock <= 0:
            # 庫存耗盡，記錄時間 (使用線性插值可以更準確，但為簡潔使用步進時間)
            sell_out_times_minutes.append(time_elapsed_minutes)
        else:
            # 超過最大模擬時間仍未售罄
            sell_out_times_minutes.append(MAX_SIMULATION_MINUTES)

    # 4. 計算中位數售罄時間 (避免極端值影響)，並轉換成小時
    if not sell_out_times_minutes:
        return -1 # 預測失敗

    median_sell_out_minutes = np.median(sell_out_times_minutes)
    
    # 如果預計能撐超過 48 小時，回傳一個大數字999 (前端會顯示「庫存充足」)
    if median_sell_out_minutes >= MAX_SIMULATION_MINUTES:
        return 999.0

    # 回傳結果，取一位小數
    return round(median_sell_out_minutes / 60, 1)'''

def _forecast_stock(pid):
    """
    使用 NumPy 向量化加速蒙地卡羅模擬。
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    row = cursor.execute("SELECT remaining_qty FROM products WHERE id=?", (pid,)).fetchone()
    conn.close()

    if not row: return -1
    current_stock = row["remaining_qty"]
    if current_stock <= 0: return 0

    # 設定參數
    n_sims = NUM_SIMULATIONS  # 1000
    max_steps = 48 * 60 // int(UPDATE_INTERVAL / 60) # 預設最多模擬 48 小時的步數
    
    # --- 向量化核心開始 ---
    
    # 1. 一次生成所有模擬所需的隨機需求矩陣 (Shape: 1000 x max_steps)
    # 假設 DEMAND_MIN=0, DEMAND_MAX=3
    demands = np.random.randint(DEMAND_MIN, DEMAND_MAX + 1, size=(n_sims, max_steps))
    
    # 2. 計算累積消耗量 (Cumulative Sum)
    cumulative_demands = np.cumsum(demands, axis=1)
    
    # 3. 找出消耗量超過當前庫存的時間點
    # (cumulative_demands >= current_stock) 會回傳布林矩陣
    # argmax 會回傳第一個 True 的索引 (即售罄的步數)
    sold_out_indices = (cumulative_demands >= current_stock).argmax(axis=1)
    
    # 處理那些「到了 max_steps 還沒賣完」的情況 (argmax 在全 False 時會回傳 0，需修正)
    # 檢查最後一步是否真的超過庫存
    not_sold_out = cumulative_demands[:, -1] < current_stock
    
    # 將步數轉換為分鐘
    sold_out_minutes = sold_out_indices * SIMULATION_INTERVAL_MINUTES
    
    # 將沒賣完的設為最大時間
    sold_out_minutes[not_sold_out] = max_steps * SIMULATION_INTERVAL_MINUTES
    
    # --- 向量化核心結束 ---

    median_minutes = np.median(sold_out_minutes)
    
    if median_minutes >= (max_steps * SIMULATION_INTERVAL_MINUTES):
        return 999.0
        
    return round(median_minutes / 60, 1)

#推薦系統（Collaborative Filtering）
# 收藏行為 → 商品相似度
# 推薦系統相關函數
def get_item_similarity_matrix():
    """
    從收藏清單中計算商品之間的餘弦相似度矩陣。
    這個函數可以在應用程式啟動時或定時執行，以提升效能。
    """
    try:
        # 1. 取得使用者收藏資料
        favorites = query_db("SELECT user_id, product_id FROM favorites")
        print(f"從資料庫讀取的收藏資料: {favorites}")
        if not favorites:
            return None, None

        favorites_list = [dict(row) for row in favorites]

        # 2. 轉換為 Pandas DataFrame
        df = pd.DataFrame(favorites_list)
        
        # 3. 建立使用者-商品交互矩陣
        user_item_matrix = df.pivot_table(
            #favorites 表 → 使用者 × 商品矩陣
            index='product_id', 
            columns='user_id', 
            aggfunc=lambda x: 1, 
            fill_value=0
        )
        
        # 4. 計算餘弦相似度，Cosine similarity 是對「商品向量」算的
        item_similarity_matrix = cosine_similarity(user_item_matrix)
        
        # 5. 轉換回 DataFrame 以便後續查找
        item_similarity_df = pd.DataFrame(
            item_similarity_matrix,
            index=user_item_matrix.index,
            columns=user_item_matrix.index
        )
        return item_similarity_df, user_item_matrix.index.tolist()

    except Exception as e:
        print(f"計算相似度矩陣時發生錯誤: {e}")
        return None, None

# 為了效能，可以在應用程式啟動時預先計算好矩陣
similarity_matrix, product_ids = None, None
recommender_initialized = False

#第一次請求才計算，避免 server 啟動過慢
@app.before_request
def initialize_recommender():
    """
    在第一個請求進來時，初始化推薦系統的資料。
    """
    global similarity_matrix, product_ids, recommender_initialized
    if not recommender_initialized:
        similarity_matrix, product_ids = get_item_similarity_matrix()
        recommender_initialized = True
        print("已成功計算商品相似度矩陣")

# 取得相似商品
#推薦系統相關函數
def get_similar_products(product_id, n=5):
    """
    根據商品ID返回最相似的n個商品ID。
    """
    global similarity_matrix
    if similarity_matrix is None or product_id not in similarity_matrix.index:
        return []

    # 找出與該商品最相似的商品
    similar_products = similarity_matrix.loc[product_id].sort_values(ascending=False)
    # 過濾掉自己，並取前 n 個
    similar_products = similar_products[similar_products.index != product_id]
    
    result = [
        {"product_id": int(idx), "score": float(score)} 
        for idx, score in similar_products.head(n).items()
    ]
    return result

#使用者偏好系統（Category-based）
#API，使用者第一次登入會跳 Modal，存偏好類別（如：飲料、零食），可與推薦系統混合（Hybrid Recommender）
@app.post("/api/user/reco_prefs")
def api_user_reco_prefs():
    uid = session.get("user_id")
    if not uid:
        return jsonify({"ok": False, "error": "not_logged_in"}), 401

    data = request.get_json(silent=True) or {}
    # ✅ 這行改掉：優先讀 categories，兼容舊的 category
    cats = data.get("categories")
    if not isinstance(cats, list):
        cats = data.get("category", [])
    if not isinstance(cats, list):
        cats = []

    try:
        save_user_prefs(int(uid), [str(x) for x in cats])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/import_stores", methods=["POST"])
def api_import_stores():
    # For security, in production protect this endpoint (auth/roles). Kept open here for demo/dev.
    file = request.files.get("file")
    brand = request.form.get("brand") or ""
    if not file:
        return jsonify({"ok": False, "error": "缺少檔案"}), 400
    # Expected CSV headers: name,address,latitude,longitude[,brand]
    import io, csv
    f = io.StringIO(file.stream.read().decode("utf-8"))
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        try:
            name = row.get("name","").strip()
            address = row.get("address","").strip()
            lat = float(row.get("latitude"))
            lng = float(row.get("longitude"))
            b = (row.get("brand") or brand or "").strip() or None
            if not name or not lat or not lng:
                continue
            # Avoid duplicates by same brand+name+lat+lng
            ex = query_db("SELECT id FROM stores WHERE name=? AND printf('%.6f',latitude)=printf('%.6f',?) AND printf('%.6f',longitude)=printf('%.6f',?) AND IFNULL(brand,'')=IFNULL(?, '')",
                          [name, lat, lng, b], one=True)
            if not ex:
                exec_db("INSERT INTO stores (name,address,latitude,longitude,brand) VALUES (?,?,?,?,?)", [name,address,lat,lng,b])
                count += 1
        except Exception as e:
            continue
    return jsonify({"ok": True, "inserted": count})

def check_and_add_column(conn):
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(accounts);")
    columns = [column[1] for column in cursor.fetchall()]
    if 'avatar_url' not in columns:
        cursor.execute("ALTER TABLE accounts ADD COLUMN avatar_url TEXT;")
        conn.commit()
"""
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    user_id = session.get("id")
    user_data = cursor.execute("SELECT username, email, avatar_url FROM accounts WHERE id = ?", (user_id,)).fetchone()
    return conn
"""
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 確保有 avatar_url 欄位
    check_and_add_column(conn)

    cursor = conn.cursor()
    user_id = session.get("id")
    user_data = None
    if user_id is not None:
        user_data = cursor.execute(
            "SELECT username, email, avatar_url FROM accounts WHERE id = ?", 
            (user_id,)
        ).fetchone()
    return conn

def get_center():
    lat = session.get("center_lat")
    lng = session.get("center_lng")
    if lat is None or lng is None:
        lat, lng = 25.033964, 121.564468
    return float(lat), float(lng)

# （可選）統一取得半徑
def get_radius_km():
    r = session.get("radius_km")
    try:
        r = float(r)
    except (TypeError, ValueError):
        r = 3.0
    return r

def query_db(query, args=(), one=False):
    con = get_db()
    cur = con.execute(query, args)
    rv = cur.fetchall()
    cur.close()
    con.close()
    return (rv[0] if rv else None) if one else rv

# 這是您之前優化後的 exec_db 結構，請確認 timeout=5 的設定
def exec_db(query, args=()):
    try:
        # 使用 timeout=5 來確保連線不會無限期等待
        with sqlite3.connect(DB_PATH, timeout=5) as con: 
            cur = con.cursor()
            cur.execute(query, args)
            con.commit()
            last_id = cur.lastrowid
            return last_id
            
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            # 這是您的日誌訊息，現在它會提示您 WAL 模式是最終解法
            print("SQLite 鎖定錯誤發生，請檢查其他長時間運行的寫入操作或啟用 WAL 模式。")
        raise e

@app.route("/")
def index():
    lat, lng = get_center()
    radius_km = get_radius_km()

    uid = session.get("user_id")
    if uid:  # 已登入才檢查
        if "show_reco_modal" in session:
            show_reco_modal = bool(session.pop("show_reco_modal"))
        else:
            show_reco_modal = not user_has_prefs(uid)
    else:
        show_reco_modal = False  # 未登入絕不顯示


    return render_template(
        "home.html",
        center_lat=lat, center_lng=lng, radius_km=radius_km,
        show_reco_modal=show_reco_modal,
        is_logged_in=bool(uid) 
    )

@app.post("/set_center")
def set_center():
    try:
        lat = float(request.form.get("lat"))
        lng = float(request.form.get("lng"))
    except (TypeError, ValueError):
        return redirect(request.referrer or url_for("home"))
    session["center_lat"] = lat
    session["center_lng"] = lng
    radius = request.form.get("radius_km")
    if radius:
        try:
            session["radius_km"] = float(radius)
        except ValueError:
            pass
    return redirect(request.referrer or url_for("home"))
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # 基本驗證
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Email 格式不正確", "error")
        elif not re.match(r'^[A-Za-z0-9_]{3,20}$', username):
            flash("用戶名需為 3-20 個字母、數字或底線", "error")
        elif len(password) < 6:
            flash("密碼至少 6 碼", "error")
        elif query_db("SELECT id FROM accounts WHERE username = ?", [username], one=True):
            flash("帳號已存在", "error")
        elif query_db("SELECT id FROM accounts WHERE email = ?", [email], one=True):
            flash("此 Email 已被使用", "error")
        else:
            # 寫入資料庫
            pw_col = _accounts_password_col()
            pw_val = generate_password_hash(password)

            try:
                con = sqlite3.connect(_db_path())
                cur = con.cursor()
                # 盡量包含建立時間；若沒有該欄位也會照常寫入
                columns = f"(username, email, {pw_col}, created_at)"
                placeholders = "(?, ?, ?, CURRENT_TIMESTAMP)"
                try:
                    cur.execute(
                        f"INSERT INTO accounts {columns} VALUES {placeholders}",
                        (username, email, pw_val),
                    )
                except sqlite3.OperationalError:
                    # 沒有 created_at 欄位時退回三欄
                    cur.execute(
                        f"INSERT INTO accounts (username, email, {pw_col}) VALUES (?, ?, ?)",
                        (username, email, pw_val),
                    )
                con.commit()
            except sqlite3.IntegrityError:
                # 若表上有 UNIQUE(username/email) 會拋這個
                flash("帳號或 Email 已存在", "error")
            except Exception as e:
                flash(f"資料庫錯誤：{e}", "error")
            finally:
                try:
                    con.close()
                except:
                    pass

            if "_flashes" not in session:  # 沒錯誤才算成功
                flash("註冊成功，請登入", "ok")
                return redirect(url_for("index"))

    return render_template("register.html")
@app.route("/logout")
def logout():
    session.clear()
    flash("已登出", "ok")
    return redirect(url_for("index"))

@app.route("/api/categories")
def api_categories():
    rows = query_db("SELECT DISTINCT COALESCE(category,'') AS category FROM products ORDER BY category")
    # 回傳非空類別
    cats = [r["category"] for r in rows if r["category"]]
    return jsonify(cats)

#商品搜尋（SQL 重點）
@app.route("/api/products/search")
def api_product_search():
    q         = (request.args.get("q") or "").strip()
    category  = (request.args.get("category") or "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    limit     = request.args.get("limit", default=100, type=int)
    sort_by   = request.args.get('sort', '')

    user_lat = request.args.get('lat', type=float)
    user_lng = request.args.get('lng', type=float)

    sql = """
    SELECT p.id, p.name, p.image_url, p.price, p.category,p.store_id AS store_id,
           s.name AS store_name, s.brand, s.address, s.latitude, s.longitude,
           p.remaining_qty,
           COALESCE((SELECT AVG(rating) FROM product_reviews r WHERE r.product_id = p.id), 0) AS avg_rating,
           IFNULL(sp.discount_rate, 1.0) AS discount_rate,
           CASE WHEN sp.discount_rate IS NULL 
                THEN p.price 
                ELSE ROUND(p.price * sp.discount_rate, 2) 
           END AS final_price
    """

    params = []

    # 如果有定位，才算距離
    if user_lat is not None and user_lng is not None:
        sql += """,
        ROUND(
            6371 * 2 * ASIN(
                SQRT(
                  POWER(SIN(RADIANS((s.latitude  - ?)/2.0)), 2) +
                  COS(RADIANS(?)) * COS(RADIANS(s.latitude)) *
                  POWER(SIN(RADIANS((s.longitude - ?)/2.0)), 2)
            )
        ), 2
    ) AS distance_km
        """
        params.extend([user_lat, user_lat, user_lng])
    else:
        sql += ", NULL AS distance_km"

    sql += """
    FROM products p
    JOIN stores s ON s.id = p.store_id
    LEFT JOIN specials sp ON sp.product_id = p.id
                         AND sp.store_id = p.store_id
                         AND sp.end_date >= date('now')
    WHERE 1=1
    """

    # 搜尋條件
    if q:
        sql += " AND p.name LIKE ?"
        params.append(f"%{q}%")
    if category:
        sql += " AND p.category = ?"
        params.append(category)
    if min_price is not None:
        sql += " AND (CASE WHEN sp.discount_rate IS NULL THEN p.price ELSE ROUND(p.price*sp.discount_rate,2) END) >= ?"
        params.append(min_price)
    if max_price is not None:
        sql += " AND (CASE WHEN sp.discount_rate IS NULL THEN p.price ELSE ROUND(p.price*sp.discount_rate,2) END) <= ?"
        params.append(max_price)

    # 排序方式
    if sort_by == 'price_asc':
        sql += " ORDER BY final_price ASC"
    elif sort_by == 'rating_desc':
        sql += " ORDER BY avg_rating DESC"
    elif sort_by == 'remain_qty':
        sql += " ORDER BY p.remaining_qty DESC"
    elif sort_by == 'distance' and user_lat is not None and user_lng is not None:
        sql += " ORDER BY distance_km ASC"
    else:
        sql += " ORDER BY sp.discount_rate ASC, avg_rating DESC, p.remaining_qty DESC, final_price ASC"

    sql += " LIMIT ?"
    params.append(limit)

    rows = query_db(sql, params)
    return jsonify([dict(r) for r in rows])

def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            # 記住原本要去的 URL，登入成功後導回
            session["next"] = request.url
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


@app.route("/home")
@login_required
def home():
    return index()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = query_db("SELECT * FROM accounts WHERE username = ?", [username], one=True)
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["show_reco_modal"] = (not user_has_prefs(user["id"]))

            flash("登入成功！", "ok")
            next_url = session.pop("next", None)
            return redirect(next_url or url_for("home"))
        else:
            flash("帳號或密碼錯誤", "error")

    return render_template("login.html")

"""
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "update_profile":
            # 處理個人資料更新...
            new_username = request.form.get("username", "").strip()
            new_email = request.form.get("email", "").strip()

            if not new_username or not new_email:
                flash("用戶名和Email都是必填的。", "error")
            else:
                existing_user = cursor.execute("SELECT id FROM accounts WHERE username = ? AND id != ?", (new_username, user_id)).fetchone()
                if existing_user:
                    flash("用戶名已被使用。", "error")
                else:
                    cursor.execute("UPDATE accounts SET username = ?, email = ? WHERE id = ?", (new_username, new_email, user_id))
                    conn.commit()
                    session["username"] = new_username
                    flash("個人資料已成功更新！", "ok")

        elif action == "update_preferences":
            # 處理推薦商品依據更新
            selected_categories = request.form.getlist("categories")
            
            cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
            
            for cat in selected_categories:
                cursor.execute("INSERT INTO user_preferences (user_id, category) VALUES (?, ?)", (user_id, cat))
            
            conn.commit()
            flash("推薦商品依據已更新！", "ok")

        return redirect(url_for("profile"))

    # GET 請求時，獲取使用者資料和偏好設定
    user_data = cursor.execute("SELECT username, email, avatar_url FROM accounts WHERE id = ?", (user_id,)).fetchone()    
    
    # 關鍵修改：將元組列表轉換為字串列表
    raw_preferences = cursor.execute("SELECT category FROM user_preferences WHERE user_id = ?", (user_id,)).fetchall()
    user_preferences = [pref[0] for pref in raw_preferences]

    all_categories = [row[0] for row in cursor.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL").fetchall()]
    return render_template("profile.html", user=user_data, user_preferences=user_preferences, all_categories=all_categories)

"""

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user_id = session.get("user_id")
    conn = get_db()
    cursor = conn.cursor()
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "update_profile":
            # 處理個人資料更新...
            new_username = request.form.get("username", "").strip()
            new_email = request.form.get("email", "").strip()

            if not new_username or not new_email:
                flash("用戶名和Email都是必填的。", "error")
            else:
                existing_user = cursor.execute("SELECT id FROM accounts WHERE username = ? AND id != ?", (new_username, user_id)).fetchone()
                if existing_user:
                    flash("用戶名已被使用。", "error")
                else:
                    cursor.execute("UPDATE accounts SET username = ?, email = ? WHERE id = ?", (new_username, new_email, user_id))
                    conn.commit()
                    session["username"] = new_username
                    flash("個人資料已成功更新！", "ok")

        elif action == "update_preferences":
            # 處理推薦商品依據更新
            selected_categories = request.form.getlist("categories")
            
            cursor.execute("DELETE FROM user_preferences WHERE user_id = ?", (user_id,))
            
            for cat in selected_categories:
                cursor.execute("INSERT INTO user_preferences (user_id, category) VALUES (?, ?)", (user_id, cat))
            
            conn.commit()
            flash("推薦商品依據已更新！", "ok")

        conn.close()
        return redirect(url_for("profile"))

    # GET 請求時，獲取使用者資料和偏好設定
    user_data = cursor.execute("SELECT username, email, avatar_url FROM accounts WHERE id = ?", (user_id,)).fetchone()
    
    # 將元組轉換為字典，以便在模板中用名稱訪問
    user = {
        'username': user_data[0],
        'email': user_data[1],
        'avatar_url': user_data[2]
    }
    
    # 關鍵修改：將元組列表轉換為字串列表
    raw_preferences = cursor.execute("SELECT category FROM user_preferences WHERE user_id = ?", (user_id,)).fetchall()
    user_preferences = [pref[0] for pref in raw_preferences]

    all_categories = [row[0] for row in cursor.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL").fetchall()]
    conn.close()
    
    return render_template("profile.html", user=user, user_preferences=user_preferences, all_categories=all_categories)


@app.route("/profile/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    user_id = session["user_id"]
    conn = get_db()
    cursor = conn.cursor()

    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # 基礎驗證
        if not all([current_password, new_password, confirm_password]):
            flash("所有密碼欄位都是必填的。", "error")
        elif new_password != confirm_password:
            flash("新密碼與確認密碼不符。", "error")
        elif len(new_password) < 6:
            flash("新密碼長度至少為6個字元。", "error")
        else:
            # 取得舊密碼的 hash，並驗證
            user = cursor.execute("SELECT password_hash FROM accounts WHERE id = ?", (user_id,)).fetchone()

            if user and check_password_hash(user["password_hash"], current_password):
                # 更新密碼
                new_password_hash = generate_password_hash(new_password)
                cursor.execute("UPDATE accounts SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))
                conn.commit()
                flash("密碼已成功變更！", "ok")
                return redirect(url_for("profile"))
            else:
                flash("目前密碼不正確。", "error")

    # 如果是 GET 請求，就直接重定向回個人資料頁面
    return redirect(url_for("profile"))

@app.route("/profile/change_avatar", methods=["POST"])
@login_required
def change_avatar():
    user_id = session["user_id"]
    
    # 檢查是否有檔案被上傳
    if 'avatar_file' not in request.files:
        flash("未選擇檔案", "error")
        return redirect(url_for("profile"))

    file = request.files['avatar_file']
    
    # 檢查檔名是否為空
    if file.filename == '':
        flash("未選擇檔案", "error")
        return redirect(url_for("profile"))

    # 檢查檔案類型
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
    if '.' not in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        flash("不支援的檔案類型，請上傳圖片檔 (png, jpg, jpeg, gif)。", "error")
        return redirect(url_for("profile"))

    # 儲存檔案
    filename = secure_filename(f"{user_id}.{file.filename.rsplit('.', 1)[1].lower()}")
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # 更新資料庫中的頭像路徑
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE accounts SET avatar_url = ? WHERE id = ?", 
        (f"avatars/{filename}", user_id)   # <── 這裡改成存相對路徑
    )
    conn.commit()
    conn.close()
    
    flash("頭像已成功更新！", "ok")
    return redirect(url_for("profile"))


@app.route("/store/<int:store_id>")
@login_required
def store_page(store_id):
    store = query_db("SELECT * FROM stores WHERE id = ?", [store_id], one=True)
    if not store:
        return "店家不存在", 404
    products = query_db(
        """
        SELECT p.*, 
               IFNULL(s.discount_rate, 1.0) AS discount_rate,
               CASE WHEN s.discount_rate IS NULL THEN p.price ELSE ROUND(p.price * s.discount_rate,2) END AS final_price,
               s.end_date AS discount_end,
               COALESCE((SELECT AVG(rating) FROM product_reviews r WHERE r.product_id = p.id), 0) AS avg_rating,
               COALESCE((SELECT COUNT(*) FROM product_reviews r WHERE r.product_id = p.id), 0) AS rating_count
        FROM products p
        LEFT JOIN specials s ON s.product_id = p.id AND s.store_id = ? AND s.end_date >= date('now')
        WHERE p.store_id = ?
        ORDER BY final_price ASC
        """,
        [store_id, store_id]
    )
    return render_template("store.html", store=store, products=products)

import urllib.parse

@app.route("/go/store/<int:store_id>")
@login_required
def go_store(store_id: int):
    store = query_db("SELECT id, address, latitude, longitude FROM stores WHERE id = ?", [store_id], one=True)
    if not store:
        flash("找不到店家", "danger")
        return redirect(url_for("home"))  # 你的首頁路由名若不同，改這裡

    if store["latitude"] is not None and store["longitude"] is not None:
        destination = f'{store["latitude"]},{store["longitude"]}'
    else:
        destination = urllib.parse.quote(store["address"] or "")

    maps_url = f"https://www.google.com/maps/dir/?api=1&destination={destination}"
    return redirect(maps_url, code=302)

#收藏與分析（Insights）
@app.route("/favorites/insights")
@login_required
def favorites_insights():
    return render_template("favorites_insights.html")

@app.route("/api/fav_stats")
@login_required
def api_fav_stats():
    uid = session["user_id"]

    # 各類別喜愛數
    top_categories = query_db("""
      SELECT p.category, COUNT(*) AS count
      FROM favorites f JOIN products p ON p.id=f.product_id
      WHERE f.user_id=?
      GROUP BY p.category ORDER BY count DESC LIMIT 10
    """, [uid])

    # 品牌分布
    brand_dist = query_db("""
      SELECT s.brand, COUNT(*) AS count
      FROM favorites f JOIN products p ON p.id=f.product_id
      JOIN stores s ON s.id=p.store_id
      WHERE f.user_id=?
      GROUP BY s.brand ORDER BY count DESC
    """, [uid])

    # 喜愛時間序列（日）
    timeline = query_db("""
      SELECT strftime('%Y-%m-%d', f.created_at) AS day, COUNT(*) AS count
      FROM favorites f
      WHERE f.user_id=?
      GROUP BY day ORDER BY day
    """, [uid])

    # 門市 Top（依被喜愛的商品數）
    top_stores = query_db("""
      SELECT s.name as store_name, s.brand, COUNT(*) AS count
      FROM favorites f JOIN products p ON p.id=f.product_id
      JOIN stores s ON s.id=p.store_id
      WHERE f.user_id=?
      GROUP BY s.id ORDER BY count DESC LIMIT 10
    """, [uid])

    # 評分 vs 喜愛（若你有 product_reviews）
    rating_vs = query_db("""
      SELECT ROUND(AVG(r.rating),1) AS avg_rating, COUNT(*) AS fav_count
      FROM favorites f
      JOIN products p ON p.id=f.product_id
      LEFT JOIN product_reviews r ON r.product_id=p.id
      WHERE f.user_id=?
    """, [uid])

    return jsonify({
      "top_categories": [dict(x) for x in top_categories],
      "brand_dist":     [dict(x) for x in brand_dist],
      "timeline":       [dict(x) for x in timeline],
      "top_stores":     [dict(x) for x in top_stores],
      "rating_vs":      dict(rating_vs or {}) if rating_vs else {}
    })

@app.route("/favorites")
@login_required
def favorites_page():
    return render_template("favorites.html")

@app.route("/api/favorites", methods=["GET"])
@login_required
def api_favorites():
    uid = session["user_id"]
    rows = query_db("""
        SELECT 
            f.id as fav_id, f.created_at,
            p.id as product_id, p.name, p.image_url, p.price, p.category, p.remaining_qty as remaining_qty,
            s.name as store_name, s.brand, s.address,
            pr.avg_rating,
            
            -- ** 新增：折扣率和最終價格的計算 (假設折扣率欄位為 discount_value) **
            IFNULL(sp.discount_rate, 1.0) AS discount_rate,
            CASE WHEN sp.discount_rate IS NULL 
                 THEN p.price 
                 ELSE ROUND(p.price * sp.discount_rate, 2) 
            END AS final_price
            
        FROM favorites f
        JOIN products p ON p.id = f.product_id
        JOIN stores s ON s.id = p.store_id
        
        -- 聯結評分
        LEFT JOIN (
            SELECT product_id, AVG(rating) AS avg_rating
            FROM product_reviews
            GROUP BY product_id
        ) pr ON pr.product_id = p.id
        
        -- ** 核心修正：聯結特價資訊 **
        LEFT JOIN specials sp ON sp.product_id = p.id
                             AND sp.store_id = p.store_id
                             AND sp.end_date >= date('now') -- 只篩選尚未過期的特價
                             
        WHERE f.user_id = ?
        ORDER BY f.created_at DESC
    """, [uid])
    return jsonify([dict(r) for r in rows])

@app.route("/api/favorites/add", methods=["POST"])
@login_required
def api_favorites_add():
    uid = session["user_id"]
    pid = int(request.form["product_id"])
    exec_db("INSERT OR IGNORE INTO favorites (user_id, product_id) VALUES (?,?)", [uid, pid])
    return jsonify({"ok": True})

@app.route("/api/favorites/add_notify", methods=["POST"])
@app.route("/api/favorites/add_notify/", methods=["POST"])
@login_required
def api_favorites_add_notify():
    try:
        data = request.get_json(silent=True) or {}
        pid_raw = (request.form.get("product_id") if request.form else None) or data.get("product_id")
        if not pid_raw:
            return jsonify({"ok": False, "error": "missing product_id"}), 400
        pid = int(pid_raw)

        uid = session["user_id"]

        # ⚠️ 若你的 specials 有 store_id，改用含同店條件那個 SQL（下面有給）
        sale = query_db("""
            WITH normalized AS (
                SELECT
                    p.id    AS product_id,
                    p.name  AS product_name,
                    p.price AS price,
                    CASE
                      WHEN sp.discount_rate IS NULL THEN NULL
                      WHEN CAST(sp.discount_rate AS REAL) > 1.5
                           THEN CAST(sp.discount_rate AS REAL) / 100.0   -- 80 → 0.8
                      ELSE CAST(sp.discount_rate AS REAL)                 -- 0.8 → 0.8
                    END AS effective_rate,
                    DATE(COALESCE(NULLIF(REPLACE(sp.end_date,'/','-'),''), '9999-12-31')) AS end_date_norm
                FROM products p
                JOIN specials sp ON sp.product_id = p.id           -- 先不限制同店
                WHERE p.id = ?
            )
            SELECT product_name, price, effective_rate,
                   ROUND(price * effective_rate, 2) AS final_price,
                   end_date_norm
            FROM normalized
            WHERE effective_rate BETWEEN 0.00001 AND 0.99999
              AND end_date_norm >= DATE('now')
            ORDER BY effective_rate ASC, end_date_norm DESC
            LIMIT 1
        """, [pid], one=True)

        # 沒特價 → 不寫通知
        if not sale:
            return jsonify({"ok": True, "sale": False})

        # 有特價 → 寫通知
        pname = sale["product_name"]
        msg = f"你加入喜好項目的「{pname}」正在特價，現在只要 {sale['final_price']}！"
        exec_db(
            "INSERT INTO notifications (user_id, message, product_id, product_name) VALUES (?,?,?,?)",
            [uid, msg, pid, pname]
        )

        return jsonify({
            "ok": True,
            "sale": True,
            "product": {
                "id": pid,
                "name": pname,
                "final_price": sale["final_price"],
                "discount_rate": sale["effective_rate"],
                "discount_end": sale["end_date_norm"],
            }
        })

    except Exception as e:
        # 回傳可見錯誤，讓你在 Network 面板直接看到原因
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/favorites/remove", methods=["POST"])
@login_required
def api_favorites_remove():
    uid = session["user_id"]
    pid = int(request.form["product_id"])
    exec_db("DELETE FROM favorites WHERE user_id=? AND product_id=?", [uid, pid])
    return jsonify({"ok": True})

'''
@app.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    uid = session["user_id"]
    if request.method == "POST":
        cats = request.form.getlist("categories")
        exec_db("DELETE FROM user_preferences WHERE user_id = ?", [uid])
        for c in cats:
            exec_db(
                "INSERT INTO user_preferences (user_id, category, weight) VALUES (?, ?, 1.0)",
                [uid, c],
            )
        flash("偏好已儲存！", "ok")
        return redirect(url_for("home"))

    exist = query_db("SELECT category FROM user_preferences WHERE user_id = ?", [uid])
    checked = [row["category"] for row in exist]
    return render_template("onboarding.html", checked=checked)
'''

@app.route("/recommend")
def recommend_page():
    return render_template("recommend.html")

@app.route("/api/stores")
def api_stores():
    rows = query_db(
        """
        SELECT s.id, s.name, s.address, s.latitude, s.longitude, s.brand,
               COALESCE(SUM(p.remaining_qty), 0) as remaining_qty
        FROM stores s
        LEFT JOIN products p ON p.store_id = s.id
        GROUP BY s.id
        """
    )
    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)
    radius = request.args.get("radius", default=3.0, type=float)
    brand = request.args.get("brand")
    out = []
    for r in rows:
        d = None
        if lat is not None and lng is not None:
            d = haversine(lat, lng, r["latitude"], r["longitude"])
            if d > radius: continue
        if brand and (r["brand"] or "").lower() != brand.lower():
            continue
        item = dict(r)
        if d is not None:
            item["distance_km"] = round(d, 3)
        out.append(item)
    return jsonify(out)


@app.route("/product/<int:pid>", methods=["GET", "POST"])
@login_required
def product_page(pid):
    uid = session["user_id"]
    # 讀商品 + 店名
    product = query_db(
        "SELECT p.*, st.name as store_name "
        "FROM products p JOIN stores st ON st.id = p.store_id "
        "WHERE p.id = ?", [pid], one=True
    )
    if not product:
        return "找不到商品", 404

    # 送出評價
    if request.method == "POST":
        rating = int(request.form.get("rating", 0))
        comment = (request.form.get("comment") or "").strip()
        rating = max(1, min(5, rating))
        exec_db(
            "INSERT INTO product_reviews (user_id, product_id, rating, comment) VALUES (?,?,?,?)",
            [uid, pid, rating, comment]
        )
        flash("感謝你的評價！", "ok")
        return redirect(url_for("product_page", pid=pid))

    # 顯示平均分/評論列表
    reviews = query_db(
        "SELECT r.*, a.username "
        "FROM product_reviews r JOIN accounts a ON a.id = r.user_id "
        "WHERE r.product_id = ? ORDER BY r.created_at DESC", [pid]
    )
    avg = query_db(
        "SELECT AVG(rating) as avg, COUNT(*) as cnt "
        "FROM product_reviews WHERE product_id = ?", [pid], one=True
    )
    return render_template("product.html", product=product, reviews=reviews, avg=avg)

@app.route("/api/recommendations")
def api_recommend():
    uid = session.get("user_id")            # 可為 None（訪客）
    brand = (request.args.get("brand") or "").lower()
    limit = int(request.args.get("limit", 12))

    rows = query_db(
        """
        WITH prefs AS (
            SELECT category, weight FROM user_preferences WHERE user_id = ?
        ),
        hist AS (
            -- 用 favorites 當歷史偏好來源
            SELECT p.category AS category, COUNT(*) AS q
            FROM favorites f
            JOIN products p ON p.id = f.product_id
            WHERE (? IS NOT NULL) AND f.user_id = ?
            GROUP BY p.category
        ),
        prefscore1 AS (
            -- 合併使用者偏好 + 歷史收藏
            SELECT category,
                   COALESCE(weight,0) + COALESCE((SELECT q FROM hist WHERE hist.category = prefs.category),0) AS score
            FROM prefs
            UNION
            SELECT category, q FROM hist WHERE category NOT IN (SELECT category FROM prefs)
        ),
        store_agg AS (
            SELECT s.id AS store_id, s.name AS store_name, s.address, s.latitude, s.longitude, s.brand,
                   COALESCE(SUM(p.remaining_qty),0) AS store_remaining
            FROM stores s LEFT JOIN products p ON p.store_id = s.id
            GROUP BY s.id
        )
        SELECT
            p.id AS product_id, p.name, p.image_url, p.price, p.category, p.store_id,
            sa.store_name, sa.address, sa.latitude, sa.longitude, sa.brand, sa.store_remaining,
            COALESCE((SELECT AVG(rating) FROM product_reviews r WHERE r.product_id = p.id), 0) AS avg_rating,
            COALESCE((SELECT COUNT(*) FROM product_reviews r WHERE r.product_id = p.id), 0) AS rating_count,
            IFNULL(sp.discount_rate, 1.0) AS discount_rate,
            CASE WHEN sp.discount_rate IS NULL THEN p.price ELSE ROUND(p.price * sp.discount_rate, 2) END AS final_price,
            COALESCE((SELECT score FROM prefscore1 WHERE category = p.category), 0) AS pref_score
        FROM products p
        JOIN store_agg sa ON sa.store_id = p.store_id
        LEFT JOIN specials sp ON sp.product_id = p.id AND sp.store_id = p.store_id AND sp.end_date >= date('now')
        WHERE
          (
            ? = '' OR
            (LOWER(REPLACE(REPLACE(IFNULL(sa.brand,''),' ',''),'-','')) LIKE '%7eleven%'   AND ? = '7-11') OR
            (LOWER(REPLACE(REPLACE(IFNULL(sa.brand,''),' ',''),'-','')) LIKE '%familymart%' AND ? = 'familymart') OR
            (LOWER(REPLACE(REPLACE(IFNULL(sa.brand,''),' ',''),'-','')) LIKE '%hilife%'     AND ? = 'hilife') OR
            (LOWER(REPLACE(REPLACE(IFNULL(sa.brand,''),' ',''),'-','')) LIKE '%okmart%'     AND ? = 'okmart')
          )
        ORDER BY
          pref_score DESC,
          sa.store_remaining DESC,
          discount_rate ASC,
          final_price ASC
        LIMIT ?
        """,
        [
            uid,         # prefs.user_id
            uid, uid,    # hist：保護訪客（uid=None時 hist 為空）
            brand, brand, brand, brand, brand,
            limit
        ]
    )
    return jsonify([dict(r) for r in rows])


@app.route("/api/notifications")
@login_required
def api_notifications():
    uid = session["user_id"]
    rows = query_db("SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 50", [uid])
    return jsonify([dict(r) for r in rows])
@app.route("/notifications")
@login_required
def notifications_page():
    rows = query_db(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC",
        [session["user_id"]]
    )
    return render_template("notifications.html", notifs=rows)


@app.route("/api/trigger_hotspot_notif", methods=["POST"])
@login_required
def api_trigger_hotspot_notif():
    uid = session["user_id"]
    store = query_db(
        """
        SELECT s.name, COALESCE(SUM(p.remaining_qty),0) rem
        FROM stores s LEFT JOIN products p ON p.store_id = s.id
        GROUP BY s.id
        ORDER BY rem DESC
        LIMIT 1
        """,
        one=True
    )
    if store and store["rem"] >= 50:
        exec_db("INSERT INTO notifications (user_id, message) VALUES (?, ?)", [uid, f"附近「{store['name']}」剩餘大量商品，已通知合作機構協助消耗。"])
        return jsonify({"ok": True, "message": "觸發成功"})
    return jsonify({"ok": False, "message": "目前沒有大量剩餘的店家"}), 400

@app.context_processor
def inject_user():
    return {"current_user": session.get("username")}

@app.cli.command("initdb")
def initdb():
    with open(os.path.join(os.path.dirname(__file__), "schema.sql"), "r", encoding="utf-8") as f:
        schema = f.read()
    con = sqlite3.connect(DB_PATH)
    con.executescript(schema)
    con.commit()
    con.close()
    print("DB initialized.")

@app.route("/api/spotlight_products")
def api_spotlight_products():
    uid     = session.get("user_id")
    lat     = float(request.args.get("lat", 25.033968))
    lng     = float(request.args.get("lng", 121.564468))
    radius  = float(request.args.get("radius", 3))
    brand_in = (request.args.get("brand") or "").strip().lower()
    limit   = int(request.args.get("limit", 12))

    # ---- 將前端品牌字串正規化成一個關鍵字（空字串 = 不過濾）----
    bnorm = brand_in.replace(" ", "").replace("-", "")
    norm_brand = ""
    if bnorm:
        if ("7" in bnorm and ("11" in bnorm or "eleven" in bnorm)) or "seven" in bnorm:
            norm_brand = "7-11"         # 這裡只是一個「使用者輸入」代表，真正比對用 sa.norm_brand
        elif "family" in bnorm or "全家" in brand_in:
            norm_brand = "familymart"
        elif "hilife" in bnorm or "hi-life" in brand_in or "萊爾富" in brand_in:
            norm_brand = "hilife"
        elif "okmart" in bnorm or bnorm == "ok" or "ok超商" in brand_in:
            norm_brand = "okmart"
        else:
            norm_brand = bnorm  # 其他字串就當關鍵字

    sql = """
    WITH prefs AS (
        SELECT category, weight FROM user_preferences WHERE user_id = ?
    ),
    hist AS (
        SELECT p.category, COUNT(*) AS q
        FROM favorites f
        JOIN products p ON p.id = f.product_id
        WHERE (? IS NOT NULL) AND f.user_id = ?
        GROUP BY p.category
    ),
    prefscore AS (
        SELECT category,
               COALESCE(weight,0) + COALESCE((SELECT q FROM hist WHERE hist.category=prefs.category),0) AS score
        FROM prefs
        UNION
        SELECT category, q FROM hist WHERE category NOT IN (SELECT category FROM prefs)
    ),
    store_agg AS (
        SELECT
            s.id AS store_id, s.name AS store_name, s.address,
            s.latitude, s.longitude,
            s.brand,
            LOWER(REPLACE(REPLACE(IFNULL(s.brand,''),' ',''),'-','')) AS norm_brand,
            COALESCE(SUM(p.remaining_qty),0) AS store_remaining
        FROM stores s
        LEFT JOIN products p ON p.store_id = s.id
        GROUP BY s.id
    ),
    prod AS (
        SELECT
            p.id AS product_id, p.name, p.image_url, p.price, p.category, p.store_id,
            sa.store_name, sa.address, sa.latitude, sa.longitude, sa.brand, sa.norm_brand,
            sa.store_remaining,
            IFNULL(sp.discount_rate, 1.0) AS discount_rate,
            CASE WHEN sp.discount_rate IS NULL THEN p.price ELSE ROUND(p.price * sp.discount_rate, 2) END AS final_price,
            COALESCE((SELECT AVG(rating) FROM product_reviews r WHERE r.product_id = p.id), 0) AS avg_rating,
            COALESCE((SELECT COUNT(*) FROM product_reviews r WHERE r.product_id = p.id), 0) AS rating_count,
            COALESCE((SELECT score FROM prefscore WHERE category = p.category), 0) AS pref_score,

            6371 * 2 * ASIN(
              SQRT(
                POWER(SIN(RADIANS((sa.latitude  - ?)/2.0)), 2) +
                COS(RADIANS(?)) * COS(RADIANS(sa.latitude)) *
                POWER(SIN(RADIANS((sa.longitude - ?)/2.0)), 2)
              )
            ) AS distance_km
        FROM products p
        JOIN store_agg sa ON sa.store_id = p.store_id
        LEFT JOIN specials sp
               ON sp.product_id = p.id
              AND sp.store_id   = p.store_id
              AND sp.end_date  >= date('now')
        WHERE
          (
            ? = '' OR
            (
              /* 7-11：容許 7eleven / 711 / 7-11 等寫法 */
              (sa.norm_brand LIKE '%7eleven%' OR sa.norm_brand LIKE '%711%')
              AND ? IN ('7-11','7-eleven','7eleven','711')
            ) OR
            (
              /* FamilyMart：容許 familymart / 全家 */
              (sa.norm_brand LIKE '%familymart%')
              AND ? IN ('familymart','全家')
            ) OR
            (
              /* Hi-Life：容許 hilife / hi-life / 萊爾富 */
              (sa.norm_brand LIKE '%hilife%')
              AND ? IN ('hilife','hi-life','hi life','萊爾富')
            ) OR
            (
              /* OKmart：容許 okmart / ok */
              (sa.norm_brand LIKE '%okmart%')
              AND ? IN ('okmart','ok')
            )
          )
    )
    SELECT *
    FROM prod
    WHERE distance_km <= ?
    ORDER BY
      pref_score DESC,
      store_remaining DESC,
      discount_rate ASC,
      distance_km ASC,
      final_price ASC
    LIMIT ?;
    """

    # 參數順序「一定要」與 SQL 中的 ? 對齊
    params = [
        # prefs/hist
        uid,         # prefs.user_id
        uid, uid,    # hist: (? IS NOT NULL) 以及 f.user_id = ?

        # 距離計算
        lat, lat, lng,

        # 品牌比對（第一個為空字串代表不過濾）
        norm_brand,  # ? = ''
        norm_brand,  # 7-11 群
        norm_brand,  # familymart 群
        norm_brand,  # hilife 群
        norm_brand,  # okmart 群

        # 半徑與筆數
        radius,
        limit
    ]

    rows = query_db(sql, params)
    return jsonify([dict(r) for r in rows])

try:
    from .ai_client import ask_model  # when used as package
except ImportError:
    from ai_client import ask_model
def _recommend_today_specials(limit:int=5):
    """
    取出未過期、仍有庫存、且有折扣(s.discount_rate < 1.0)的特價品。
    回傳每項 dict：{name, store_name, price, discount_rate, final_price, remaining_qty, end_date}
    """
    import sqlite3, os, datetime
    db_path = os.path.join(os.path.dirname(__file__), "app.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    today = datetime.date.today().isoformat()
    cur.execute("""
        SELECT p.name, p.price, p.remaining_qty,
               s.discount_rate, s.end_date,
               st.name AS store_name
        FROM specials s
        JOIN products p ON p.id = s.product_id
        JOIN stores st ON st.id = s.store_id
        WHERE s.end_date >= ?
          AND p.remaining_qty > 0
          AND s.discount_rate < 1.0
        ORDER BY s.discount_rate ASC, p.price DESC
        LIMIT ?
    """, (today, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    # 算出折後價（final_price）
    for r in rows:
        try:
            r["final_price"] = round(float(r["price"]) * float(r["discount_rate"]), 2)
        except Exception:
            r["final_price"] = r["price"]
    return rows

def _answer_for_food_question(q:str):
    """
    問「今天吃什麼？」或相近語句 -> 回 DB 推薦；否則回 None。
    """
    import re
    if not q:
        return None
    qn = q.strip().lower()
    patterns = [
        r"今天.*吃什麼", r"晚餐.*吃什麼", r"中午.*吃什麼", r"吃什麼好", r"推薦.*(特價|打折|優惠)"
    ]
    if any(re.search(p, q, flags=re.I) for p in patterns) or "what should i eat" in qn:
        try:
            items = _recommend_today_specials(limit=6)
        except Exception as e:
            # 若資料表或欄位還沒建好，回友善訊息
            return f"讀取特價資料時發生錯誤：{e}"
        if not items:
            return "目前資料庫沒有特價品或庫存不足，建議查看「🔍 商品」頁面。"
        lines = ["今天的特價推薦："]
        for it in items:
            line = f"• {it['store_name']}｜{it['name']}：原價 {it['price']:.0f}，折扣 {it['discount_rate']:.2f} ➜ 約 {it['final_price']:.0f}（剩 {it['remaining_qty']}）"
            lines.append(line)
        return "\n".join(lines)
    return None
@app.route("/api/ai_ask", methods=["POST"])
def api_ai_ask():
    try:
        data = request.get_json(silent=True) or {}
        question = (data.get("question") or "").strip()
        if not question:
            return jsonify({"ok": False, "error": "缺少 question"}), 400

        referer = request.headers.get("Origin") or request.headers.get("Referer") or ""
        title = "Food Map AI Helper"

        ans = _answer_for_food_question(question)
        if ans is None:
            ans = ask_model(question, referer=referer, title=title)
        return jsonify({"ok": True, "answer": ans})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/favorites/item_recommend")
@login_required
def api_item_recommend():
    uid = session["user_id"]
    limit = int(request.args.get("limit", 12))

    # 使用字典來儲存推薦商品ID及其來源（是從哪個收藏商品推薦來的）
    recommended_products_with_reasons = defaultdict(list)

    # 1. 找出使用者已收藏的商品
    favorited_products = query_db("SELECT product_id, name FROM favorites f JOIN products p ON p.id = f.product_id WHERE f.user_id=?", [uid]) or []
    if not favorited_products:
        return jsonify({"ok": True, "recommendations": []})

    # 2. 對每個收藏商品，找出最相似的商品
    for fav in favorited_products:
        pid = fav["product_id"]
        pname = fav["name"]
        
        # 呼叫修改後的函式，會回傳 ID 和分數
        similar_items = get_similar_products(pid, n=5) or []
        
        for item in similar_items:
            # 儲存推薦來源
            recommended_products_with_reasons[item["product_id"]].append({
                "source_product_id": pid,
                "source_product_name": pname,
                "score": item["score"]
            })

    # 3. 排除使用者已經收藏的商品
    existing_pids = {fav["product_id"] for fav in favorited_products}
    final_pids_to_recommend = list(recommended_products_with_reasons.keys() - existing_pids)

    if not final_pids_to_recommend:
        return jsonify({"ok": True, "recommendations": []})

    # 4. 查詢商品資訊
    placeholders = ",".join(["?"] * len(final_pids_to_recommend))
    sql = f"""
        SELECT 
            p.id, p.name, p.image_url, p.price, p.category, 
            s.name AS store_name, s.brand,
            COALESCE((SELECT AVG(rating) FROM product_reviews r WHERE r.product_id = p.id), 0) AS avg_rating,
            IFNULL(sp.discount_rate, 1.0) AS discount_rate,
            CASE WHEN sp.discount_rate IS NULL 
                 THEN p.price 
                 ELSE ROUND(p.price * sp.discount_rate, 2) 
            END AS final_price
        FROM products p
        JOIN stores s ON s.id = p.store_id
        LEFT JOIN specials sp ON sp.product_id = p.id
                             AND sp.store_id = p.store_id
                             AND sp.end_date >= date('now') -- 篩選尚未過期的特價
        WHERE p.id IN ({placeholders})
        LIMIT ?
    """
    params = final_pids_to_recommend + [limit]
    db_results = query_db(sql, params) or []

    # 5. 將推薦原因合併到最終結果
    final_recommendations = []
    for row in db_results:
        rec_item = dict(row)
        rec_item["reasons"] = recommended_products_with_reasons[row["id"]]
        final_recommendations.append(rec_item)
    
    # 你可以選擇對結果進行排序，例如根據相似度分數
    final_recommendations.sort(key=lambda x: max(r['score'] for r in x['reasons']), reverse=True)

    return jsonify({"ok": True, "recommendations": final_recommendations})

# 猜你想搜
@app.route("/api/popular_products")
@login_required
def api_popular_categories():
    uid = session["user_id"]
    
    # 這裡的 SQL 查詢只從 favorites 表中抓取類別
    sql = """
    SELECT p.name
    FROM favorites f
    JOIN products p ON f.product_id = p.id
    WHERE f.user_id = ?
    GROUP BY p.name
    ORDER BY COUNT(*) DESC
    LIMIT 5;
    """

    params = [uid]
    rows = query_db(sql, params)
    
    # 只回傳類別名稱的列表
    return jsonify([row['name'] for row in rows])

__ensure_notifications_schema()

#庫存預測
@app.route("/api/forecast/<int:pid>")
def api_forecast(pid):
    try:
        # 呼叫預測函式
        sell_out_time = _forecast_stock(pid)
        
        message = "" 

        # 根據回傳值，提供不同的訊息
        if sell_out_time == 0:
            now = datetime.now()
            next_restock_dt = None

            # 找出今天或明天最接近的補貨時間點 (假設 RESTOCK_TIMES 已定義)
            for rh, rm in RESTOCK_TIMES:
                restock_dt = now.replace(hour=rh, minute=rm, second=0, microsecond=0)
                if restock_dt > now:
                    next_restock_dt = restock_dt
                    break

            # 如果今天沒有了，就從明天的第一個時間點開始
            if next_restock_dt is None:
                rh, rm = RESTOCK_TIMES[0]
                next_restock_dt = now.replace(hour=rh, minute=rm, second=0, microsecond=0) + timedelta(days=1)

            # 計算距離下次進貨的時間 (分鐘)
            time_to_restock_minutes = (next_restock_dt - now).total_seconds() / 60
            
            # 庫存為 0 的時候，回傳下次進貨時間（用負數表示）
            sell_out_time = -round(time_to_restock_minutes / 60, 1)
            message = "庫存為 0，預計稍後補貨"

        elif sell_out_time == -1:
            message = "商品不存在或無法預測"
        else:
            # 預計售罄時間 > 0 的情況
            if sell_out_time >= 24:
                message = "庫存充足 (24小時以上)"
            else:
                message = f"預計 {sell_out_time} 小時內售罄"

        # 確保在成功路徑上回傳 JSON
        return jsonify({"ok": True, "message": message, "sell_out_time_hours": sell_out_time})
    
    except Exception as e:
        # 捕捉所有運行時錯誤，並回傳明確的錯誤訊息
        # 這個錯誤會被寫入您的伺服器日誌（如果有的話），並回傳給前端
        print(f"FATAL Error in api_forecast for PID {pid}: {e}")
        # 【修正目標】：回傳 500 錯誤狀態，前端會收到這個明確的 JSON
        return jsonify({"ok": False, "message": f"預測伺服器內部崩潰: {e}", "sell_out_time_hours": -999.0}), 500

if __name__ == "__main__":
    # 啟動背景線程
    t = threading.Thread(target=update_stock, daemon=True)
    t.start()

    # 確保資料庫結構存在
    __ensure_notifications_schema()

    # 🌟 啟動背景任務
    start_background_tasks()
    app.run(host="0.0.0.0", port=5000, debug=True)
