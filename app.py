import streamlit as st
import psycopg2
from sqlalchemy import create_engine
from contextlib import contextmanager
import pandas as pd
import os
import time
import base64  # 🌟 改用 base64，這是可逆的編碼套件
import requests  # 🌟 新增：用於向 API 查詢 IP 的地理位置
import datetime
import extra_streamlit_components as stx
from psycopg2 import pool  # 👈 🌟 請加入這一行，引入高速連線池套件

# --- 密碼編解碼工具 ---
def encode_pw(pw):
    """將密碼編碼隱藏 (存入資料庫時使用)"""
    return base64.b64encode(pw.encode('utf-8')).decode('utf-8')

def decode_pw(pw_encoded):
    """將密碼解碼回明文 (顯示在後台畫面上時使用)"""
    try:
        return base64.b64decode(pw_encoded.encode('utf-8')).decode('utf-8')
    except:
        return pw_encoded  # 萬一解碼失敗，就顯示原字串

# --- 1. 基礎設定與整地 ---
if not os.path.exists("product_images"): os.makedirs("product_images")
st.set_page_config(page_title="強盛集團 ERP", layout="wide", initial_sidebar_state="expanded")

# 👇 覆蓋開始：升級為企業級專業 ERP 視覺視覺語法 (修復側邊欄按鈕字體隱形問題) 👇
enterprise_erp_style = """
            <style>
            /* 1. 隱藏 Streamlit 官方浮水印與徽章 */
            footer {visibility: hidden;}    
            div[class^="viewerBadge_container"] { display: none !important; }
            div[class^="styles_viewerBadge"] { display: none !important; }
            .viewerBadge_container__1QSob { display: none !important; }
            .styles_viewerBadge__1yB5_ { display: none !important; }
            
            /* 2. 全域字體與專業商務背景 */
            html, body, [data-testid="stAppViewContainer"] {
                font-family: "Inter", "Segoe UI", "SF Pro Display", "Microsoft JhengHei", sans-serif !important;
                background-color: #F4F6F9 !important;
            }
            
            /* 3. 側邊欄 (Sidebar) 企業化高階深色調 */
            [data-testid="stSidebar"] {
                background-color: #0F172A !important; 
                border-right: 1px solid #1E293B !important;
            }
            /* 🌟 確保側邊欄大部分字體是白色 */
            [data-testid="stSidebar"] * {
                color: #F8FAFC !important;
            }
            /* 🌟 排除條款：強制一般按鈕維持深黑色 */
            [data-testid="stSidebar"] button[kind="secondary"] * {
                color: #0F172A !important;
            }
            /* 🌟 確保側邊欄輸入框、下拉選單的文字與背景不被全域白色覆蓋 */
            [data-testid="stSidebar"] input,
            [data-testid="stSidebar"] input[type="number"],
            [data-testid="stSidebar"] div[data-baseweb="input"] input, 
            [data-testid="stSidebar"] div[data-baseweb="select"] * {
                color: #0F172A !important;
                -webkit-text-fill-color: #0F172A !important; /* 🌟 修復 Chrome/Safari 強制變白的問題 */
                background-color: #FFFFFF !important;
            }

            /* 4. 頂部功能標籤頁 (Tabs) */
            button[data-baseweb="tab"] {
                font-size: 14px !important;
                font-weight: 600 !important;
                color: #475569 !important;
                border-bottom: 2px solid transparent !important;
                padding: 10px 16px !important;
            }
            button[data-baseweb="tab"][aria-selected="true"] {
                color: #2563EB !important; 
                border-bottom: 2px solid #2563EB !important;
                background-color: rgba(37, 99, 235, 0.04) !important;
            }

            /* 5. 卡片式容器升級 (st.container) */
            div[data-testid="stElementContainer"] > div[style*="border"] {
                background-color: #FFFFFF !important;
                border: 1px solid #E2E8F0 !important;
                border-radius: 6px !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
                padding: 18px !important;
                margin-bottom: 12px !important;
            }

            /* 6. 核心數據指標 (st.metric) */
            div[data-testid="stMetric"] {
                background-color: #FFFFFF !important;
                border: 1px solid #E2E8F0 !important;
                border-radius: 6px !important;
                padding: 14px 18px !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
            }
            div[data-testid="stMetricLabel"] > div {
                color: #475569 !important; 
                font-weight: 600 !important;
            }
            div[data-testid="stMetricValue"] > div {
                color: #0F172A !important; 
                font-weight: 700 !important;
            }

            /* 7. 系統按鈕 (st.button) 結構優化 */
            button[kind="primary"] {
                background-color: #2563EB !important;
                border-radius: 4px !important;
                border: none !important;
            }
            button[kind="primary"] * {
                color: #FFFFFF !important;
                font-weight: 600 !important;
            }
            button[kind="primary"]:hover { background-color: #1D4ED8 !important; }
            
            button[kind="secondary"] {
                background-color: #FFFFFF !important;
                border-radius: 4px !important;
                border: 1px solid #CBD5E1 !important;
            }
            button[kind="secondary"] * {
                color: #0F172A !important;
                font-weight: 500 !important;
            }
            button[kind="secondary"]:hover {
                border-color: #94A3B8 !important;
                background-color: #F8FAFC !important;
            }

            /* 8. 確保所有輸入框的文字是深色，背景是白色 */
            div[data-baseweb="input"],
            div[data-baseweb="input"] input, 
            div[data-baseweb="select"] div,
            textarea {
                color: #0F172A !important;
                background-color: #FFFFFF !important;
                border-radius: 4px !important;
            }
            
            /* 🌟 終極修正：暴力鎖定所有 Streamlit 的 + / - 按鈕 (包含 SVG, Button, Div 結構)，強制顯示深黑色！ */
            [data-testid="stNumberInputStepDown"], 
            [data-testid="stNumberInputStepUp"],
            [data-testid="stNumberInputStepDown"] svg, 
            [data-testid="stNumberInputStepUp"] svg,
            div[data-baseweb="input"] button,
            div[data-baseweb="input"] button svg,
            div[data-baseweb="input"] div[role="button"],
            div[data-baseweb="input"] div[role="button"] svg {
                fill: #0F172A !important;
                color: #0F172A !important;
            }
            </style>
            """
st.markdown(enterprise_erp_style, unsafe_allow_html=True)
# 👆 覆蓋結束 👆

# --- 2. 穩定的資料庫連線 (終極智能包裝器 + 高速連線池) ---
@st.cache_resource
def get_connection_pool():
    # 🌟 建立執行緒安全的連線池，並加入 Keepalives 心跳機制，防止雲端連線超時中斷！
    return pool.ThreadedConnectionPool(
        1, 20, 
        st.secrets["DB_URL"],
        keepalives=1,
        keepalives_idle=30,     # 閒置 30 秒後開始發送心跳確認
        keepalives_interval=10, # 每 10 秒發送一次
        keepalives_count=5      # 允許失敗 5 次
    )

class PostgresCursorWrapper:
    def __init__(self, cursor):
        self.cursor = cursor
        
    def execute(self, query, params=None):
        pg_query = query.replace("?", "%s")
        if "INSERT OR REPLACE INTO products" in pg_query:
            pg_query = pg_query.replace("INSERT OR REPLACE INTO products", "INSERT INTO products")
            pg_query += " ON CONFLICT (編碼) DO UPDATE SET 類別=EXCLUDED.類別, 品牌=EXCLUDED.品牌, 名稱=EXCLUDED.名稱, 備註=EXCLUDED.備註, 圖片路徑=EXCLUDED.圖片路徑"
            
        if params:
            self.cursor.execute(pg_query, params)
        else:
            self.cursor.execute(pg_query)
        return self
        
    def __getattr__(self, attr):
        return getattr(self.cursor, attr)

class PostgresConnWrapper:
    def __init__(self, conn):
        self.conn = conn
    def cursor(self):
        return PostgresCursorWrapper(self.conn.cursor())
    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur
    def commit(self):
        self.conn.commit()
    def close(self):
        pass # 🌟 重要魔法：把 close 留空。交給連線池管理，不強制掛斷電話

@contextmanager
def get_db():
    db_pool = get_connection_pool()
    conn = db_pool.getconn() # 從池子裡「借」一條已經連線好的專線
    try:
        yield PostgresConnWrapper(conn)
    finally:
        db_pool.putconn(conn) # 🌟 執行完畢後把專線「還」給池子，保持暢通
        
# 給 Pandas 專用的引擎
db_engine = create_engine(st.secrets["DB_URL"].replace("postgres://", "postgresql://"))
    
# --- 3. 初始化資料庫與預設權限 ---
@st.cache_resource
def init_db_v7():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. 建立系統核心表格
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, nickname TEXT DEFAULT '', last_active REAL DEFAULT 0, admin_remark TEXT DEFAULT '')''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS permissions (role TEXT, module TEXT, can_view BOOLEAN, can_edit BOOLEAN, can_upload BOOLEAN, can_download BOOLEAN)''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_perms (username TEXT, module TEXT, can_view BOOLEAN DEFAULT FALSE, can_edit BOOLEAN DEFAULT FALSE, can_upload BOOLEAN DEFAULT FALSE, can_download BOOLEAN DEFAULT FALSE, PRIMARY KEY (username, module))''')
        
        # 2. 商品資料表
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (編碼 TEXT PRIMARY KEY, 類別 TEXT, 品牌 TEXT, 名稱 TEXT, 備註 TEXT, 圖片路徑 TEXT)''')
        
        # 3. 庫存管理表 (SQLite 的 AUTOINCREMENT 在 PG 叫做 SERIAL)
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (id SERIAL PRIMARY KEY, 編碼 TEXT, 倉庫位置 TEXT, 數量 INTEGER, 單支成本_RMB REAL, 採購廠商 TEXT, 採購金額_RMB REAL, 進貨日期 DATE)''')
        
        # 4. 匯率設定表 (取代 INSERT OR IGNORE)
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL)''')
        cursor.execute("INSERT INTO settings (key, value) VALUES ('exchange_rate', 4.5) ON CONFLICT (key) DO NOTHING")
        
        # 5. 採購單與明細表
        cursor.execute('''CREATE TABLE IF NOT EXISTS procurement_orders (order_id TEXT PRIMARY KEY, date DATE, supplier TEXT, total_qty INTEGER, total_amount_rmb REAL, total_amount_twd REAL, warehouse TEXT, staff TEXT, status TEXT DEFAULT '待驗收')''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS procurement_items (id SERIAL PRIMARY KEY, order_id TEXT, code TEXT, qty INTEGER, unit_price_rmb REAL, total_price_rmb REAL)''')

        # 6. 動態倉庫與日誌表
        cursor.execute('''CREATE TABLE IF NOT EXISTS warehouses (name TEXT PRIMARY KEY)''')
        cursor.execute("SELECT count(*) FROM warehouses")
        if cursor.fetchone()[0] == 0:
            for w in ['台灣黃興-商品', '東莞熙元-商品', '台灣黃興-樣品', '退換貨倉']:
                cursor.execute("INSERT INTO warehouses (name) VALUES (%s) ON CONFLICT (name) DO NOTHING", (w,))
                
        cursor.execute('''CREATE TABLE IF NOT EXISTS login_logs (id SERIAL PRIMARY KEY, username TEXT, login_time TEXT, ip TEXT, location TEXT, device TEXT)''')
        
        # 7. 預設 Admin 帳號
        cursor.execute("INSERT INTO users (username, password, nickname, role) VALUES ('admin', %s, '總管理員', 'Admin') ON CONFLICT (username) DO NOTHING", (encode_pw('123456'),))
        
        # 8. 日誌表
        cursor.execute('''CREATE TABLE IF NOT EXISTS product_logs (id SERIAL PRIMARY KEY, timestamp TEXT, operator TEXT, action_type TEXT, details TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory_logs (id SERIAL PRIMARY KEY, timestamp TEXT, operator TEXT, action_type TEXT, details TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS system_logs (id SERIAL PRIMARY KEY, timestamp TEXT, module TEXT, operator TEXT, action_type TEXT, details TEXT)''')
        
        # 9. 客戶訂單明細表
        cursor.execute('''CREATE TABLE IF NOT EXISTS customer_orders (
            訂單編號 TEXT PRIMARY KEY, 訂單日期 DATE, 訂單連結 TEXT, 姓名 TEXT, 電話 TEXT, 門市 TEXT, 店號 TEXT,
            品項內容 TEXT, 下單總數 INTEGER, 包裹應收 REAL, 商品成本 REAL, 物流運費 REAL, 物流運費_RMB REAL DEFAULT 0.0,
            出貨成本 REAL, 訂單損益 REAL, 物流編號 TEXT, 取貨狀態 TEXT DEFAULT '待出貨', 取貨日期 DATE,
            信箱 TEXT DEFAULT '', 顧客備註 TEXT DEFAULT '', 商家備註 TEXT DEFAULT ''
        )''')
        
        # 👇 新增 10. 每日廣告費紀錄表 👇
        cursor.execute('''CREATE TABLE IF NOT EXISTS daily_ad_spend (
            date DATE PRIMARY KEY, 
            spend_usd REAL, 
            exchange_rate REAL, 
            spend_twd REAL
        )''')
        # 👆 新增結束 👆

        conn.commit()
        
init_db_v7()

# --- 日誌自動寫入工具群 ---
def log_inventory_change(operator, action_type, details):
    with get_db() as conn:
        conn.execute("INSERT INTO inventory_logs (timestamp, operator, action_type, details) VALUES (%s, %s, %s, %s)", (time.strftime('%Y-%m-%d %H:%M:%S'), operator, action_type, details))
        conn.commit()
        
def log_product_change(operator, action_type, details):
    with get_db() as conn:
        conn.execute("INSERT INTO product_logs (timestamp, operator, action_type, details) VALUES (%s, %s, %s, %s)", (time.strftime('%Y-%m-%d %H:%M:%S'), operator, action_type, details))
        conn.commit()

def log_system_action(module, operator, action_type, details):
    with get_db() as conn:
        conn.execute("INSERT INTO system_logs (timestamp, module, operator, action_type, details) VALUES (%s, %s, %s, %s, %s)", (time.strftime('%Y-%m-%d %H:%M:%S'), module, operator, action_type, details))
        conn.commit()

# --- 自動抓取並記錄登入歷程工具 ---
def log_login_event(username):
    try:
        headers = st.context.headers
        ip_raw = headers.get("X-Forwarded-For", "")
        if ip_raw:
            ip = ip_raw.split(",")[0].strip()
        else:
            ip = "127.0.0.1"
        device = headers.get("User-Agent", "未知裝置/瀏覽器")
    except Exception:
        ip, device = "127.0.0.1", "本地運行環境/無法辨識裝置"

    location = "未知地點"
    
    # 判斷是否為本地端或私人網段 (包含 IPv6 的 ::1)
    is_local = not ip or ip == "127.0.0.1" or ip == "::1" or ip.startswith("192.168.") or ip.startswith("10.")

    try:
        if is_local:
            # 🌟 如果是本機端測試，不帶特定 IP，讓 API 自動偵測你目前上網的真實 Public IP
            api_url = "http://ip-api.com/json/?lang=zh-TW"
        else:
            # 🌟 如果是實際上線部署，帶入抓取到的訪客真實 IP
            api_url = f"http://ip-api.com/json/{ip}?lang=zh-TW"
            
        response = requests.get(api_url, timeout=5).json()
        
        if response.get("status") == "success":
            if is_local:
                # 把本機的 127.0.0.1 替換成 API 查到的真實對外 IP
                ip = response.get('query', ip) 
                
            country = response.get('country', '')
            city = response.get('city', response.get('regionName', ''))
            location = f"{country}－{city}" if city else country
            
            # 如果是本機測試，可以在地點後方加個小標記方便辨識
            if is_local:
                location += " (本機測試)"
        else:
            location = "內部/私人網路區間"
    except Exception:
        location = "地理定位查詢超時"

    with get_db() as conn:
        conn.execute("INSERT INTO login_logs (username, login_time, ip, location, device) VALUES (?, ?, ?, ?, ?)", 
                     (username, time.strftime('%Y-%m-%d %H:%M:%S'), ip, location, device))
        conn.commit()

# --- 🌟 4. 全新顆粒化權限檢查工具 ---
def check_perm(role_string, module, action="can_view"):
    """動態檢查當前登入者是否具備特定模組的 View/Edit/Upload/Download 權限"""
    if str(role_string) == "Admin": 
        return True
    
    # 抓取登入時存在 Session 的權限字典
    perms = st.session_state.get('perms', {})
    mod_perms = perms.get(module, {})
    return bool(mod_perms.get(action, False))

# --- 5. 系統登入 ---
# --- 🌟 初始化 Cookie 管理器 ---
cookie_manager = stx.CookieManager(key="cookie_manager")

# 👇 🌟 終極殺手鐧：強迫系統在剛打開網頁時等待，確保抓到瀏覽器的 Cookie 👇
if 'cookie_synced' not in st.session_state:
    with st.spinner("🔄 正在安全驗證連線與同步環境..."):
        st.session_state['cookie_synced'] = True
        time.sleep(1)  # 放寬至 1 秒，確保手機 APP (較慢) 的 Webview 也能成功掛載
        st.rerun()
# 👆 殺手鐧結束 👆

TIMEOUT_SECONDS = 3 * 3600  # 核心設定：3 小時完全無動作即判定超時 (3小時 * 3600秒)

# 1. 狀況 A：如果目前已經在登入狀態中，持續監控當前操作是否超時，並即時同步至資料庫
if 'logged_in' in st.session_state and st.session_state['logged_in']:
    current_time = time.time()
    last_active = st.session_state.get('last_active', current_time)
    
    # 檢查是否在不知不覺中閒置超過 3 小時
    if current_time - last_active > TIMEOUT_SECONDS:
        username_to_clear = st.session_state.get('user')
        st.session_state.clear()
        if cookie_manager.get('erp_auto_login'):
            cookie_manager.delete('erp_auto_login', key="del_cookie_timeout")
        with get_db() as conn:
            # 🌟 這裡的 username_to_clear 也務必確認有加上 str()
            conn.execute("UPDATE users SET last_active = 0 WHERE username = ?", (str(username_to_clear),))
            conn.commit()
        st.warning("⚠️ 由於長時間未操作，為保護系統安全，已為您自動登出。")
        time.sleep(2)
        st.rerun()
    else:
        # 有任何點擊或切換模組的短時間操作，刷新 Session 暫存，並立刻回寫資料庫存檔
        st.session_state['last_active'] = current_time
        with get_db() as conn:
            # 🌟 這裡加上 str()，防止純數字帳號讓 PostgreSQL 崩潰
            conn.execute("UPDATE users SET last_active = ? WHERE username = ?", (current_time, str(st.session_state['user'])))
            conn.commit()

# 2. 狀況 B：若網頁剛被重開 (Session 暫存全空)，嘗試由 Cookie 與資料庫時間核對進行安全登入
if 'logged_in' not in st.session_state:
    auto_login_user = cookie_manager.get(cookie="erp_auto_login")
    
    # 🌟 偵錯提示：如果 Cookie 抓不到，嘗試強迫瀏覽器重新整理一次
    if auto_login_user:
        with get_db() as conn:
            cursor = conn.cursor()
            # 🌟 第 1 處修改
            cursor.execute("SELECT role, nickname, last_active FROM users WHERE username = %s", (str(auto_login_user),))
            res = cursor.fetchone()
            if res:
                user_role, user_nick, db_last_active = res[0], res[1], (res[2] if res[2] else 0)
                
                if time.time() - db_last_active < TIMEOUT_SECONDS:
                    # 🌟 第 2 處修改：加上 str()
                    cursor.execute("SELECT module, can_view, can_edit, can_upload, can_download FROM user_perms WHERE username=?", (str(auto_login_user),))
                    perms_data = cursor.fetchall()
                    perm_dict = {row[0]: {'can_view': bool(row[1]), 'can_edit': bool(row[2]), 'can_upload': bool(row[3]), 'can_download': bool(row[4])} for row in perms_data}
                    
                    st.session_state.update({
                        'logged_in': True, 'role': user_role, 'user': auto_login_user, 
                        'nickname': user_nick if user_nick else auto_login_user, 'perms': perm_dict,
                        'last_active': time.time()
                    })
                    # 🌟 第 3 處修改：加上 str()
                    conn.execute("UPDATE users SET last_active = ? WHERE username = ?", (time.time(), str(auto_login_user)))
                    conn.commit()
                    st.rerun() # 成功登入，重整進入系統
                else:
                    cookie_manager.delete('erp_auto_login', key="del_cookie_expired")
    else:
        # 🌟 如果這時候還是沒抓到，且不是第一次進入，可能是被 Chrome 攔截了
        # 我們設定一個標記，強制跳過一次重新嘗試
        if 'retry_count' not in st.session_state:
            st.session_state['retry_count'] = 1
            st.rerun() # 這裡會強制讓網頁閃爍一次，讓 Chrome 有第二次機會加載 Cookie
            
# 3. 狀況 C：完全未登入或已超時，顯示傳統登入介面
if 'logged_in' not in st.session_state:
    st.title("📦 強盛集團 | ERP 系統")
    
    mode = st.radio("請選擇模式", ["登入", "註冊"], horizontal=True)
    
    if mode == "登入":
        with st.form("login_form"):
            user = st.text_input("帳號", autocomplete="username")
            pw = st.text_input("密碼", type="password", autocomplete="current-password")
            
            keep_logged_in = st.checkbox("記住帳號密碼", value=True)
            
            if st.form_submit_button("登入"):
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT role, nickname FROM users WHERE username=%s AND password=%s", (user, encode_pw(pw)))
                    res = cursor.fetchone()
                    if res:
                        user_role, user_nick = res[0], res[1]
                        
                        cursor.execute("SELECT module, can_view, can_edit, can_upload, can_download FROM user_perms WHERE username=?", (user,))
                        perms_data = cursor.fetchall()
                        perm_dict = {row[0]: {'can_view': bool(row[1]), 'can_edit': bool(row[2]), 'can_upload': bool(row[3]), 'can_download': bool(row[4])} for row in perms_data}
                        
                        current_now = time.time()
                        st.session_state.update({
                            'logged_in': True, 'role': user_role, 'user': user, 
                            'nickname': user_nick if user_nick else user, 'perms': perm_dict,
                            'last_active': current_now
                        })
                        
                        # 登入成功立刻把時間打入資料庫
                        cursor.execute("UPDATE users SET last_active = ? WHERE username = ?", (current_now, user))
                        conn.commit()
                        
                        # 🌟 強力修正：確保 Chrome 能寫入
                        if keep_logged_in:
                            # 嘗試多寫入一個加密後的 Session 備份，作為雙重防禦
                            st.session_state['auto_login_key'] = user
                            cookie_manager.set('erp_auto_login', user, key="set_cookie_login", max_age=604800, same_site="none", secure=True)
                        else:
                            cookie_manager.set('erp_auto_login', user, key="set_cookie_login", same_site="none", secure=True)
                        
                        time.sleep(0.5) # 確保前端寫入 Cookie
                        log_login_event(user)
                        st.rerun()
                    else:
                        st.error("帳號或密碼錯誤！")
    else: 
        with st.form("register_form"):
            new_user = st.text_input("設定新帳號", autocomplete="username")
            new_pw = st.text_input("設定新密碼", type="password", autocomplete="new-password")
            confirm_pw = st.text_input("確認密碼", type="password", autocomplete="new-password")
            
            if st.form_submit_button("註冊"):
                if not new_user or not new_pw:
                    st.error("帳號與密碼不可為空！")
                elif new_pw != confirm_pw:
                    st.error("兩次密碼輸入不一致！")
                else:
                    try:
                        with get_db() as conn:
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO users (username, password, nickname, role) VALUES (?, ?, '', 'CS')", (new_user, encode_pw(new_pw)))
                            conn.commit()
                            st.success(f"註冊成功！帳號【{new_user}】已建立，請通知管理員開放權限後登入。")
                    # 🌟 將 sqlite3 改成 psycopg2
                    except psycopg2.IntegrityError:
                        st.error("❌ 該帳號名稱已被註冊。")
    st.stop()

# --- 6. 側邊欄設計 ---
st.sidebar.title("🏢 強盛集團 ERP")

# 🌟 側邊欄顯示與修改暱稱 (僅修改自己的暱稱)
show_name = st.session_state.get('nickname', st.session_state['user'])

# 使用 HTML 與 Flexbox 確保圖示與文字絕對對齊，並帶有質感的提示框背景
st.sidebar.markdown(f"""
<div style="background-color: rgba(37,99,235,0.1); padding: 12px 16px; border-radius: 6px; border: 1px solid rgba(37,99,235,0.3); margin-bottom: 15px;">
    <div style="display: flex; align-items: center; margin-bottom: 6px;">
        <span style="min-width: 32px; font-size: 16px;">👤</span>
        <span style="font-size: 15px;">登入者： <b>{show_name}</b></span>
    </div>
    <div style="display: flex; align-items: center;">
        <span style="min-width: 32px; font-size: 16px;">🆔</span>
        <span style="font-size: 15px;">帳號： <b>{st.session_state['user']}</b></span>
    </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar.expander("✏️ 修改我的顯示暱稱"):
    new_nick = st.text_input("輸入新暱稱", value=show_name if show_name != st.session_state['user'] else "")
    if st.button("更新暱稱", use_container_width=True):
        with get_db() as conn:
            conn.execute("UPDATE users SET nickname = ? WHERE username = ?", (new_nick, st.session_state['user']))
            conn.commit()
        st.session_state['nickname'] = new_nick
        st.success("暱稱已更新！")
        time.sleep(0.5)
        st.rerun()

# 👇 更改主動登出按鈕邏輯，徹底清除 Cookie 與資料庫紀錄 👇
if st.sidebar.button("登出系統", use_container_width=True): 
    username_to_clear = st.session_state.get('user')
    st.session_state.clear()
    if cookie_manager.get('erp_auto_login'):
        cookie_manager.delete('erp_auto_login', key="del_cookie_manual")
    with get_db() as conn:
        conn.execute("UPDATE users SET last_active = 0 WHERE username = ?", (username_to_clear,))
        conn.commit()
    time.sleep(0.5) # 確保前端與資料庫寫入完畢
    st.rerun()
    
st.sidebar.divider()

# 🌟 先取得當前使用者的角色，才能進行權限判斷
role = st.session_state['role']

# 👇 1. 動態根據權限生成側邊欄選單 👇
available_modules = ["首頁"]  # 首頁預設大家都看得到

# 逐一檢查各大模組的「查看(can_view)」權限，有權限才加入選單
if check_perm(role, "商品訊息", "can_view"):
    available_modules.append("商品訊息")
if check_perm(role, "商品庫存", "can_view"):
    available_modules.append("商品庫存")
if check_perm(role, "採購管理", "can_view"):
    available_modules.append("採購管理")
if check_perm(role, "訂單明細", "can_view"):
    available_modules.append("訂單明細")
if check_perm(role, "財務報表", "can_view"):
    available_modules.append("財務報表")

# 🌟 2. 權限管理模組，強制只有 Admin 總管理員才看得見
if role == "Admin" or st.session_state.get('user') == 'admin':
    available_modules.append("權限管理")

# 👇 3. 將過濾後的可用清單渲染到側邊欄 👇
menu = st.sidebar.radio(
    "請選擇功能模組：", 
    available_modules,
    key="main_menu"
)
# 👆 動態選單替換結束 👆

# --- 7. 各大模組骨架預覽 ---

if menu == "首頁":
    st.title("🏠 營運儀表板 (Dashboard)")
    st.write("一眼掌握今日與昨日的關鍵營業數據，包含廣告成效 (ROAS) 追蹤。")
    
    # ==========================================
    # --- 1. 先把所有資料撈出來 (這樣才能放在最上面計算月度總覽) ---
    # ==========================================
    today = pd.Timestamp.today().date()
    yesterday = today - pd.Timedelta(days=1)
    
    with get_db() as conn:
        df_orders = pd.read_sql("SELECT 訂單日期, 取貨狀態, 包裹應收, 商品成本, 物流運費 FROM customer_orders", conn)
        df_ad = pd.read_sql("SELECT date, spend_twd FROM daily_ad_spend", conn)

    # 資料清洗與型別轉換
    if not df_orders.empty:
        df_orders['訂單日期_dt'] = pd.to_datetime(df_orders['訂單日期'], errors='coerce').dt.date
        df_orders['包裹應收'] = pd.to_numeric(df_orders['包裹應收'], errors='coerce').fillna(0.0)
        df_orders['商品成本'] = pd.to_numeric(df_orders['商品成本'], errors='coerce').fillna(0.0)
        df_orders['物流運費'] = pd.to_numeric(df_orders['物流運費'], errors='coerce').fillna(0.0)
        df_orders['取貨狀態'] = df_orders['取貨狀態'].fillna('待出貨')
    else:
        df_orders = pd.DataFrame(columns=['訂單日期_dt', '取貨狀態', '包裹應收', '商品成本', '物流運費'])
        
    if not df_ad.empty:
        df_ad['date_dt'] = pd.to_datetime(df_ad['date']).dt.date
    else:
        df_ad = pd.DataFrame(columns=['date_dt', 'spend_twd'])

    # ==========================================
    # --- 2. 🏆 每月營運總覽 (顯示在最上方的 10 項關鍵指標) ---
    # ==========================================
    st.markdown("### 🏆 每月營運總覽")
    
    # 建立年月選擇器 (預設為當前年月)
    c_y, c_m, _ = st.columns([1, 1, 2])
    year_options = list(range(2025, 2030))
    default_y_idx = year_options.index(today.year) if today.year in year_options else 1
    sel_y = c_y.selectbox("選擇年份", year_options, index=default_y_idx, key="month_y")
    sel_m = c_m.selectbox("選擇月份", list(range(1, 13)), index=today.month - 1, key="month_m")

    # 篩選出該月份的所有訂單與廣告費
    mask_orders_m = (pd.to_datetime(df_orders['訂單日期_dt']).dt.year == sel_y) & (pd.to_datetime(df_orders['訂單日期_dt']).dt.month == sel_m)
    df_m_orders = df_orders[mask_orders_m]
    
    mask_ad_m = (pd.to_datetime(df_ad['date_dt']).dt.year == sel_y) & (pd.to_datetime(df_ad['date_dt']).dt.month == sel_m)
    df_m_ad = df_ad[mask_ad_m]

    # --- 每月各項基礎數據計算 ---
    ad_m = df_m_ad['spend_twd'].sum() if not df_m_ad.empty else 0
    orders_cnt_m = len(df_m_orders)
    rev_m = df_m_orders['包裹應收'].sum()
    prod_cost_m = df_m_orders['商品成本'].sum()
    ship_fee_m = df_m_orders['物流運費'].sum()

    # 月度狀態篩選 (針對已簽收的實際收入)
    picked_mask_m = df_m_orders['取貨狀態'].isin(['簽收'])
    picked_cnt_m = picked_mask_m.sum()
    actual_rev_m = df_m_orders.loc[picked_mask_m, '包裹應收'].sum()
    actual_prod_m = df_m_orders.loc[picked_mask_m, '商品成本'].sum()

    # --- 10 大關鍵指標深度計算 ---
    actual_cost_m = actual_prod_m + ship_fee_m
    est_profit_m = rev_m - prod_cost_m - ship_fee_m - ad_m
    actual_profit_m = actual_rev_m - actual_cost_m - ad_m
    
    # 百分比與小數點格式轉換
    pickup_rate_m = (picked_cnt_m / orders_cnt_m * 100) if orders_cnt_m > 0 else 0
    
    est_total_cost_m = prod_cost_m + ship_fee_m + ad_m
    est_roi_m = (est_profit_m / est_total_cost_m) if est_total_cost_m > 0 else 0
    
    actual_total_cost_m = actual_cost_m + ad_m
    actual_roi_m = (actual_profit_m / actual_total_cost_m) if actual_total_cost_m > 0 else 0
    actual_roas_m = (actual_rev_m / ad_m) if ad_m > 0 else 0
    
    ad_pct_m = (ad_m / rev_m * 100) if rev_m > 0 else 0
    prod_pct_m = (prod_cost_m / rev_m * 100) if rev_m > 0 else 0

    # 渲染月度看板 (改為三排配置，避免數字被擠壓到看不見)
    with st.container(border=True):
        # 第一排：營收與利潤指標 (4個)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("營業額", f"${rev_m:,.0f}")
        m2.metric("預估利潤", f"${est_profit_m:,.0f}")
        m3.metric("實際利潤", f"${actual_profit_m:,.0f}")
        m4.metric("取件率", f"{pickup_rate_m:.1f}%")
        
        st.divider()
        
        # 第二排：成本與花費指標 (4個)
        m5, m6, m7, m8 = st.columns(4)
        m5.metric("總廣告費", f"${ad_m:,.0f}")
        m6.metric("總運費", f"${ship_fee_m:,.0f}")
        m7.metric("廣告佔比", f"{ad_pct_m:.1f}%")
        m8.metric("商品佔比", f"{prod_pct_m:.1f}%")

        st.divider()
        
        # 第三排：投資報酬率指標 (切成4格但只放3個，維持寬度比例)
        m9, m10, m11, _ = st.columns(4) 
        m9.metric("預估 ROI", f"{est_roi_m:.2f}")
        m10.metric("實際 ROI", f"{actual_roi_m:.2f}")
        m11.metric("實際 ROAS", f"{actual_roas_m:.2f}")

    st.divider()

    # ==========================================
    # --- 3. 廣告費區間輸入與漏填檢查 ---
    # ==========================================
    with st.expander("✍️ 手動輸入區間廣告費 (USD) 與 漏填檢查", expanded=False): 
        
        # 👇 升級 1：自動比對並列出漏填廣告費的日期
        if not df_orders.empty:
            # 找出有訂單的日期集合，與有廣告費的日期集合
            order_dates = set(df_orders['訂單日期_dt'].dropna())
            ad_dates = set(df_ad['date_dt'].dropna()) if not df_ad.empty else set()
            # 兩者相減，得出漏填的日期，並由舊到新排序
            missing_dates = sorted(list(order_dates - ad_dates))
        else:
            missing_dates = []
            
        if missing_dates:
            missing_str = ", ".join([d.strftime('%Y-%m-%d') for d in missing_dates[:7]])
            if len(missing_dates) > 7:
                missing_str += f" ...等共 {len(missing_dates)} 天"
            st.warning(f"⚠️ 發現有訂單但【未填廣告費】的日期：\n{missing_str}")
        else:
            st.success("✅ 太棒了！目前所有有訂單的日期皆已填寫廣告費。")

        # 👇 升級 2：區間廣告費表單
        with st.form("ad_spend_form"):
            st.caption("💡 提示：輸入這段期間的『總花費』，系統會自動幫您平均分攤到每一天。")
            c_start, c_end, c_usd, c_rate = st.columns(4)
            start_date = c_start.date_input("開始日期", value=today)
            end_date = c_end.date_input("結束日期", value=today)
            total_usd = c_usd.number_input("區間【總】花費(USD)", min_value=0.0, step=1.0)
            input_rate = c_rate.number_input("美金轉台幣匯率", value=32.0, step=0.1)
            
            if st.form_submit_button("💾 儲存並均分廣告費", type="primary", use_container_width=True):
                if start_date > end_date:
                    st.error("❌ 開始日期不能晚於結束日期！")
                else:
                    # 計算總天數與每日平均花費
                    days_diff = (end_date - start_date).days + 1
                    daily_usd = total_usd / days_diff
                    daily_twd = daily_usd * input_rate
                    
                    with get_db() as conn:
                        # 迴圈將每一天的平均花費寫入資料庫
                        for i in range(days_diff):
                            curr_d = start_date + pd.Timedelta(days=i)
                            conn.execute("""
                                INSERT INTO daily_ad_spend (date, spend_usd, exchange_rate, spend_twd) 
                                VALUES (?, ?, ?, ?) 
                                ON CONFLICT (date) DO UPDATE SET 
                                spend_usd=EXCLUDED.spend_usd, exchange_rate=EXCLUDED.exchange_rate, spend_twd=EXCLUDED.spend_twd
                            """, (str(curr_d), daily_usd, input_rate, daily_twd))
                        conn.commit()
                        
                    st.success(f"✅ 成功分攤！區間 {start_date} ~ {end_date} (共 {days_diff} 天)。每日均分台幣約為 ${daily_twd:,.0f}")
                    time.sleep(1.5)
                    st.rerun()

    st.divider()

    # ==========================================
    # --- 4. 計算今日與昨日看板數據 ---
    # ==========================================
    df_today = df_orders[df_orders['訂單日期_dt'] == today]
    df_yest = df_orders[df_orders['訂單日期_dt'] == yesterday]
    
    today_ad_row = df_ad[df_ad['date_dt'] == today]
    yest_ad_row = df_ad[df_ad['date_dt'] == yesterday]

    today_orders_cnt = len(df_today)
    today_rev = df_today['包裹應收'].sum()
    today_ad = today_ad_row['spend_twd'].sum() if not today_ad_row.empty else 0
    today_roas = (today_rev / today_ad) if today_ad > 0 else 0

    yesterday_orders_cnt = len(df_yest)
    yesterday_rev = df_yest['包裹應收'].sum()
    yesterday_ad = yest_ad_row['spend_twd'].sum() if not yest_ad_row.empty else 0
    yesterday_roas = (yesterday_rev / yesterday_ad) if yesterday_ad > 0 else 0

    # --- 3. 畫面渲染：今日/昨日看板 ---
    with st.container(border=True):
        st.markdown("#### 🟢 今日即時數據")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("今日訂單數", f"{today_orders_cnt} 筆")
        c2.metric("今日營業額", f"${today_rev:,.0f}")
        c3.metric("今日廣告費", f"${today_ad:,.0f}" if today_ad > 0 else "未輸入")
        c4.metric("今日預估 ROAS", f"{today_roas:.2f} x" if today_ad > 0 else "N/A")

    with st.container(border=True):
        st.markdown("#### 🔵 昨日總結數據")
        c5, c6, c7, c8 = st.columns(4)
        c5.metric("昨日訂單數", f"{yesterday_orders_cnt} 筆")
        c6.metric("昨日營業額", f"${yesterday_rev:,.0f}")
        c7.metric("昨日廣告費", f"${yesterday_ad:,.0f}" if yesterday_ad > 0 else "未輸入")
        c8.metric("昨日預估 ROAS", f"{yesterday_roas:.2f} x" if yesterday_ad > 0 else "N/A")

    st.divider()

    # ==========================================
    # --- 4. 單週數據詳細分析 (可自選週次) ---
    # ==========================================
    st.markdown("### 📅 單週營運詳細數據 (週一至週日)")
    
    # 👇 變更：先算出上週的日期，並設為日曆的預設值（系統依然會自動抓該週的週一）
    last_week_default = today - pd.Timedelta(days=7)
    selected_date = st.date_input("🗓️ 請點擊選擇想查看的週次 (點選該週的任一天即可)", value=last_week_default)
    selected_dt = pd.Timestamp(selected_date)
    
    # 算出選擇日期的「該週週一」
    days_since_monday = selected_dt.weekday() # 0是週一, 6是週日
    target_monday = (selected_dt - pd.Timedelta(days=days_since_monday)).date()
    
    weekly_data = []
    
    # 建立統計變數 (為了最後算合計)
    sum_orders = sum_rev = sum_prod_cost = sum_ship_fee = sum_ad = 0
    sum_picked = sum_actual_rev = sum_actual_cost = 0

    for i in range(7):
        current_d = target_monday + pd.Timedelta(days=i)
        day_str = current_d.strftime('%m/%d')
        weekday_str = ["一", "二", "三", "四", "五", "六", "日"][i]
        
        # 篩選當天訂單與廣告費
        df_d = df_orders[df_orders['訂單日期_dt'] == current_d]
        ad_d = df_ad[df_ad['date_dt'] == current_d]['spend_twd'].sum() if not df_ad.empty else 0
        
        # 基本指標
        orders_cnt = len(df_d)
        rev = df_d['包裹應收'].sum()
        prod_cost = df_d['商品成本'].sum()
        ship_fee = df_d['物流運費'].sum()
        
        # 狀態篩選 (判斷是否已簽收、已完結)
        picked_up_mask = df_d['取貨狀態'].isin(['簽收'])
        resolved_mask = df_d['取貨狀態'].isin(['簽收', '退回', '已取消', '客訴', '已上架', '已重出'])
        
        picked_cnt = picked_up_mask.sum()
        actual_rev = df_d.loc[picked_up_mask, '包裹應收'].sum()
        actual_prod_cost = df_d.loc[picked_up_mask, '商品成本'].sum()
        
        # 成本與利潤計算
        actual_cost = actual_prod_cost + ship_fee
        
        est_profit = rev - prod_cost - ship_fee - ad_d
        actual_profit = actual_rev - actual_cost - ad_d
        
        # 👇 變更：取件率直接乘以 100，轉換成 0~100 的真實百分比數值
        pickup_rate = (picked_cnt / orders_cnt * 100) if orders_cnt > 0 else 0
        actual_roas = (actual_rev / ad_d) if ad_d > 0 else 0
        
        est_total_cost = prod_cost + ship_fee + ad_d
        est_roi = (est_profit / est_total_cost) if est_total_cost > 0 else 0
        
        actual_total_cost = actual_cost + ad_d
        actual_roi = (actual_profit / actual_total_cost) if actual_total_cost > 0 else 0
        
        # 判斷當日單是否全部跑完流程
        if orders_cnt == 0:
            status_label = "-"
        elif (~resolved_mask).sum() == 0:
            status_label = "✅ 完成"
        else:
            status_label = "⏳ 進行"
            
        weekly_data.append({
            "日期": f"{day_str} ({weekday_str})", "狀態": status_label,
            "訂單總數": orders_cnt, "已簽收數": picked_cnt, "取件率": pickup_rate,
            "廣告費": ad_d, "物流運費": ship_fee, "商品成本": prod_cost,
            "營業額": rev, "預估利潤": est_profit, "預估ROI": est_roi,
            "實際收入": actual_rev, "實際成本": actual_cost, "實際利潤": actual_profit, 
            "實際ROAS": actual_roas, "實際ROI": actual_roi
        })
        
        # 累加合計數據
        sum_orders += orders_cnt; sum_picked += picked_cnt
        sum_rev += rev; sum_prod_cost += prod_cost; sum_ship_fee += ship_fee; sum_ad += ad_d
        sum_actual_rev += actual_rev; sum_actual_cost += actual_cost

    # 建立總計列
    sum_est_profit = sum_rev - sum_prod_cost - sum_ship_fee - sum_ad
    sum_actual_profit = sum_actual_rev - sum_actual_cost - sum_ad
    
    # 👇 變更：取件率合計也乘以 100
    sum_pickup_rate = (sum_picked / sum_orders * 100) if sum_orders > 0 else 0
    sum_actual_roas = (sum_actual_rev / sum_ad) if sum_ad > 0 else 0
    sum_est_total_cost = sum_prod_cost + sum_ship_fee + sum_ad
    sum_est_roi = (sum_est_profit / sum_est_total_cost) if sum_est_total_cost > 0 else 0
    sum_actual_total_cost = sum_actual_cost + sum_ad
    sum_actual_roi = (sum_actual_profit / sum_actual_total_cost) if sum_actual_total_cost > 0 else 0

    weekly_data.append({
        "日期": "🌟 該週合計", "狀態": "-", 
        "訂單總數": sum_orders, "已簽收數": sum_picked, "取件率": sum_pickup_rate,
        "廣告費": sum_ad, "物流運費": sum_ship_fee, "商品成本": sum_prod_cost,
        "營業額": sum_rev, "預估利潤": sum_est_profit, "預估ROI": sum_est_roi,
        "實際收入": sum_actual_rev, "實際成本": sum_actual_cost, "實際利潤": sum_actual_profit,
        "實際ROAS": sum_actual_roas, "實際ROI": sum_actual_roi
    })

    # 轉為 DataFrame 並在前端顯示
    df_weekly = pd.DataFrame(weekly_data)
    
    # 👇 變更：依照您的需求修改小數點與顯示格式
    st.dataframe(
        df_weekly,
        use_container_width=True,
        hide_index=True,
        column_config={
            "取件率": st.column_config.NumberColumn(format="%.1f%%", help="已簽收數 / 訂單總數"),
            "物流運費": st.column_config.NumberColumn(format="$ %.0f"),  # 移除小數點
            "預估ROI": st.column_config.NumberColumn(format="%.2f"),     # 變成 0.00 格式，拿掉 %
            "實際成本": st.column_config.NumberColumn(format="$ %.0f"),  # 移除小數點
            "實際ROI": st.column_config.NumberColumn(format="%.2f"),     # 變成 0.00 格式
            "實際ROAS": st.column_config.NumberColumn(format="%.2f"),    # 變成 0.00 格式
            "預估利潤": st.column_config.NumberColumn(format="$ %.0f"),
            "實際利潤": st.column_config.NumberColumn(format="$ %.0f"),
            "營業額": st.column_config.NumberColumn(format="$ %.0f"),
            "實際收入": st.column_config.NumberColumn(format="$ %.0f"),
            "廣告費": st.column_config.NumberColumn(format="$ %.0f"),
            "商品成本": st.column_config.NumberColumn(format="$ %.0f")
        }
    )

    # ==========================================
    # --- 5. 歷史物流代收結款核對 (每週自動總結) ---
    # ==========================================
    st.markdown("### 🚚 歷史物流代收結款核對 (每週)")
    st.caption("💡 系統已自動幫您撈取歷史以來『已簽收』的訂單，按週匯總。並自動依據包裹金額計算對應手續費，算出最終預估結款金額。")

    # 新增台幣換算人民幣的匯率輸入框
    c_rate_logi, _ = st.columns([1, 3])
    # 預設 4.5 代表 1 人民幣 = 4.5 台幣 (依您的實際請款匯率修改)
    logi_rate = c_rate_logi.number_input("💵 結款匯率 (1 人民幣 = ? 台幣)", value=4.90, step=0.01)

    # 1. 篩選出所有歷史中「已簽收」的訂單
    df_picked = df_orders[df_orders['取貨狀態'] == '簽收'].copy()

    recon_data = []

    if not df_picked.empty:
        import numpy as np
        
        # 2. 自動計算每筆訂單的手續費
        # 規則：包裹0-9999收30，10000-19999收160 (以10000為分界線)
        conditions = [
            df_picked['包裹應收'] <= 9999,
            df_picked['包裹應收'] >= 10000
        ]
        choices = [30, 160]
        df_picked['單筆手續費'] = np.select(conditions, choices, default=30)
        
        # 3. 找出該筆訂單所屬的週一與週日
        df_picked['訂單日期_dt'] = pd.to_datetime(df_picked['訂單日期_dt'])
        # 算出該日期的週一
        df_picked['週一'] = df_picked['訂單日期_dt'] - pd.to_timedelta(df_picked['訂單日期_dt'].dt.weekday, unit='D')
        df_picked['週日'] = df_picked['週一'] + pd.Timedelta(days=6)
        
        # 建立週次字串，例如 07/13-07/19
        df_picked['週次'] = df_picked['週一'].dt.strftime('%m/%d') + "-" + df_picked['週日'].dt.strftime('%m/%d')
        
        # 4. 依照「週一」分組加總數據
        df_grouped = df_picked.groupby(['週一', '週次']).agg(
            簽收單數=('包裹應收', 'size'),
            應收台幣=('包裹應收', 'sum'),
            總手續費=('單筆手續費', 'sum')
        ).reset_index()
        
        # 5. 時間排序：由新到舊 (最新的一週在最上面)
        df_grouped = df_grouped.sort_values(by='週一', ascending=False)
        
        # 6. 計算預估結款並整理為表格資料
        for _, row in df_grouped.iterrows():
            # 應結給您的台幣 = 應收台幣 - 系統算出的總手續費
            net_twd = row['應收台幣'] - row['總手續費']
            # 換算預估應收人民幣
            est_rmb = (net_twd / logi_rate) if logi_rate > 0 else 0
            
            recon_data.append({
                "週次": row['週次'],
                "簽收單數": int(row['簽收單數']),
                "應收台幣 (TWD)": float(row['應收台幣']),
                "手續費 (TWD)": float(row['總手續費']),
                "預估結款 (RMB)": float(est_rmb),
                "實際結款 (RMB)": None,  # 開放填寫
                "結款日期": None,        # 開放填寫
                "匯款日期": None         # 開放填寫
            })

    df_recon = pd.DataFrame(recon_data)

    if df_recon.empty:
        st.info("目前尚無任何『已簽收』的訂單可以核對。")
    else:
        # 👇 使用 data_editor 產生「可編輯」的表格
        st.data_editor(
            df_recon,
            use_container_width=True,
            hide_index=True,
            column_config={
                "週次": st.column_config.TextColumn(disabled=True),
                "簽收單數": st.column_config.NumberColumn(format="%d 單", disabled=True),
                "應收台幣 (TWD)": st.column_config.NumberColumn(format="$ %.0f", disabled=True),
                # 系統算好的手續費直接帶入顯示
                "手續費 (TWD)": st.column_config.NumberColumn(format="-$ %.0f", disabled=True),
                "預估結款 (RMB)": st.column_config.NumberColumn(format="¥ %.2f", disabled=True),
                
                # 以下三個欄位開放給您在網頁上直接點擊、打字、選日曆編輯
                "實際結款 (RMB)": st.column_config.NumberColumn(format="¥ %.2f"),
                "結款日期": st.column_config.DateColumn(),
                "匯款日期": st.column_config.DateColumn(),
            }
        )

elif menu == "商品訊息":
    st.title("📦 商品訊息管理")
    current_operator = st.session_state.get('user', 'admin')
    is_admin = (st.session_state.get('role') == 'Admin')  # 🌟 判斷是否為管理員
    
    if check_perm(role, "商品訊息", "can_view"):
        # 🌟 動態生成分頁：一般員工只會看到前三個，Admin 才會被 push 第四個
        tabs_list = ["📋 列表瀏覽與編輯", "➕ 新增商品", "📁 批次作業"]
        if is_admin:
            tabs_list.append("📜 變動歷程日誌 (僅管理員可見)")
            
        tabs = st.tabs(tabs_list)
        
        with tabs[0]:
            if 'edit_item_code' not in st.session_state:
                st.session_state['edit_item_code'] = None
                
            if st.session_state['edit_item_code'] is None:
                with get_db() as conn:
                    df = pd.read_sql("SELECT * FROM products ORDER BY 編碼 ASC", conn)
                
                if df.empty:
                    st.info("目前商品庫中沒有任何資料。")
                else:
                    st.subheader("🔍 篩選條件")
                    filter_col1, filter_col2 = st.columns(2)
                    
                    category_list = ["全部"] + sorted([str(x) for x in df["類別"].unique() if x and str(x).strip() != ""])
                    brand_list = ["全部"] + sorted([str(x) for x in df["品牌"].unique() if x and str(x).strip() != ""])
                    
                    selected_category = filter_col1.selectbox("選擇類別", category_list)
                    selected_brand = filter_col2.selectbox("選擇品牌", brand_list)
                    
                    filtered_df = df.copy()
                    if selected_category != "全部": filtered_df = filtered_df[filtered_df["類別"] == selected_category]
                    if selected_brand != "全部": filtered_df = filtered_df[filtered_df["品牌"] == selected_brand]
                    
                    st.divider()
                    c_info, c_batch = st.columns([1, 1])
                    c_info.caption(f"📊 顯示結果：共找到 {len(filtered_df)} 筆符合條件的商品")
                    
                    if check_perm(role, "商品訊息", "can_edit") and not filtered_df.empty:
                        with c_batch.expander("🗑️ 展開批量刪除工具"):
                            del_list = st.multiselect("請選擇要刪除的商品編碼：", filtered_df['編碼'].tolist())
                            if st.button("🚨 執行批量刪除", type="primary", use_container_width=True) and del_list:
                                with get_db() as conn:
                                    placeholders = ','.join(['?'] * len(del_list))
                                    conn.execute(f"DELETE FROM products WHERE 編碼 IN ({placeholders})", del_list)
                                    conn.commit()
                                log_product_change(current_operator, "批量刪除", f"移除了 {len(del_list)} 筆商品：{', '.join(del_list)}")
                                st.success(f"✅ 已成功批量刪除 {len(del_list)} 筆商品！")
                                time.sleep(1.5)
                                st.rerun()
                    
                    if filtered_df.empty:
                        st.warning("沒有符合此篩選條件的商品，請嘗試其他組合。")
                    else:
                        for _, row in filtered_df.iterrows():
                            with st.container(border=True):
                                img_col, info_col, remark_col, action_col = st.columns([2, 3, 5, 2])
                                if row['圖片路徑'] and os.path.exists(row['圖片路徑']):
                                    img_col.image(row['圖片路徑'], use_container_width=True)
                                else:
                                    img_col.markdown("<div style='text-align:center; color:gray; padding-top:20px;'>📷 暫無圖片</div>", unsafe_allow_html=True)
                                    
                                info_col.subheader(f"🆔 {row['編碼']}")
                                info_col.write(f"類別: {row['類別']}")
                                info_col.write(f"品牌: {row['品牌']}")
                                info_col.write(f"名稱: {row['名稱']}")
                                remark_col.write("📝 備註:")
                                remark_col.caption(row['備註'])
                                
                                with action_col:
                                    if check_perm(role, "商品訊息", "can_edit"):
                                        if st.button("✏️ 編輯", key=f"edit_{row['編碼']}", use_container_width=True):
                                            st.session_state['edit_item_code'] = row['編碼']
                                            st.rerun()
                                        if st.button("🗑️ 刪除", key=f"del_{row['編碼']}", type="primary", use_container_width=True):
                                            with get_db() as conn:
                                                conn.execute("DELETE FROM products WHERE 編碼=?", (row['編碼'],))
                                                conn.commit()
                                            log_product_change(current_operator, "單筆刪除", f"移除了商品：{row['編碼']} - {row['名稱']}")
                                            st.toast(f"已成功刪除商品：{row['編碼']}！")
                                            time.sleep(1)
                                            st.rerun()
            else:
                edit_code = st.session_state['edit_item_code']
                if st.button("🔙 放棄修改並返回列表"):
                    st.session_state['edit_item_code'] = None
                    st.rerun()
                st.divider()
                
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 類別, 品牌, 名稱, 備註, 圖片路徑 FROM products WHERE 編碼=?", (edit_code,))
                    target = cursor.fetchone()
                
                if target:
                    st.subheader(f"✏️ 編輯商品：{edit_code}")
                    with st.form("edit_single_form"):
                        col_a, col_b = st.columns(2)
                        edit_cat = col_a.text_input("類別", value=target[0])
                        edit_brand = col_b.text_input("品牌", value=target[1])
                        edit_name = st.text_input("商品名稱", value=target[2])
                        edit_remark = st.text_area("備註說明", value=target[3])
                        edit_img = st.file_uploader("更換圖片 (若不更換請留空)", type=['jpg', 'png', 'jpeg'])
                        
                        if st.form_submit_button("💾 儲存修改", type="primary"):
                            new_path = target[4]
                            if edit_img:
                                new_path = f"product_images/{edit_code}.jpg"
                                with open(new_path, "wb") as f: f.write(edit_img.getbuffer())
                            
                            with get_db() as conn:
                                conn.execute("UPDATE products SET 類別=?, 品牌=?, 名稱=?, 備註=?, 圖片路徑=? WHERE 編碼=?", (edit_cat, edit_brand, edit_name, edit_remark, new_path, edit_code))
                                conn.commit()
                            
                            log_msg = f"更新了商品 {edit_code} 資料。"
                            if edit_name != target[2]: log_msg += f" 名稱: {target[2]} ➔ {edit_name}。"
                            if edit_cat != target[0]: log_msg += f" 類別: {target[0]} ➔ {edit_cat}。"
                            if edit_brand != target[1]: log_msg += f" 品牌: {target[1]} ➔ {edit_brand}。"
                            log_product_change(current_operator, "編輯商品", log_msg)
                            
                            st.success(f"✅ 商品 {edit_code} 資料已成功更新！")
                            st.session_state['edit_item_code'] = None
                            time.sleep(1.5)
                            st.rerun()
                
        with tabs[1]:
            if check_perm(role, "商品訊息", "can_edit"):
                st.subheader("➕ 新增單筆商品")
                with st.form("add_new_form", clear_on_submit=True):
                    code = st.text_input("商品編碼 (必填，不可與現有商品重複)")
                    col_a, col_b = st.columns(2)
                    category = col_a.text_input("類別")
                    brand = col_b.text_input("品牌")
                    name = st.text_input("商品名稱")
                    remark = st.text_area("備註說明")
                    img_file = st.file_uploader("上傳商品圖片", type=['jpg', 'png', 'jpeg'])
                    
                    if st.form_submit_button("💾 確認新增"):
                        if not code:
                            st.error("❌ 商品編碼為必填項目！")
                        else:
                            try:
                                path = f"product_images/{code}.jpg" if img_file else ""
                                if img_file:
                                    with open(path, "wb") as f: f.write(img_file.getbuffer())
                                
                                with get_db() as conn:
                                    conn.execute("INSERT INTO products (編碼, 類別, 品牌, 名稱, 備註, 圖片路徑) VALUES (?,?,?,?,?,?)", (code, category, brand, name, remark, path))
                                    conn.commit()
                                
                                log_product_change(current_operator, "新增單筆", f"建檔了新商品：{code} - {name} (品牌: {brand})")
                                st.success(f"🎉 成功新增商品：【{code}】 {name}！")
                                time.sleep(1.5)
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error(f"❌ 錯誤：編碼 【{code}】 已經存在！如需修改請至『列表瀏覽』點擊編輯。")
            else:
                st.error("🚫 您沒有編輯商品的權限")

        with tabs[2]:
            st.subheader("📥 批量下載完整商品表")
            if check_perm(role, "商品訊息", "can_download"):
                with get_db() as conn:
                    df_all = pd.read_sql("SELECT 編碼, 類別, 品牌, 名稱, 備註 FROM products ORDER BY 編碼 ASC", conn)
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_all.to_excel(writer, index=False, sheet_name='Sheet1')
                
                st.download_button(label="💾 下載商品清單 (Excel格式)", data=output.getvalue(), file_name="products.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            
            st.divider()
            st.subheader("📤 批量上傳商品資料")
            if check_perm(role, "商品訊息", "can_upload"):
                uploaded_file = st.file_uploader("選擇上傳檔案 (支援 CSV 或 Excel)", type=["csv", "xlsx"])
                if uploaded_file and st.button("🚀 執行批量匯入", type="primary"):
                    try:
                        df_new = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file, engine='openpyxl')
                        df_insert = df_new[["編碼", "類別", "品牌", "名稱", "備註"]].fillna("---")
                        with get_db() as conn:
                            cursor = conn.cursor()
                            for _, row in df_insert.iterrows():
                                cursor.execute("SELECT 圖片路徑 FROM products WHERE 編碼=?", (str(row["編碼"]),))
                                img_res = cursor.fetchone()
                                existing_img = img_res[0] if img_res else ""
                                cursor.execute("INSERT OR REPLACE INTO products (編碼, 類別, 品牌, 名稱, 備註, 圖片路徑) VALUES (?,?,?,?,?,?)", (str(row["編碼"]), str(row["類別"]), str(row["品牌"]), str(row["名稱"]), str(row["備註"]), existing_img))
                            conn.commit()
                        log_product_change(current_operator, "批量匯入", f"透過 Excel/CSV 檔案批次更新/新增了 {len(df_insert)} 筆商品資料")
                        st.success("✅ 批量商品資料匯入完成！")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 匯入錯誤：{str(e)}")
            else:
                st.error("🚫 您沒有上傳商品的權限")

        # 🌟 僅有 Admin 能展開與觀看的隱藏分頁
        if is_admin:
            with tabs[3]:
                st.subheader("📜 商品異動審查軌跡 (Admin 專屬)")
                st.write("此處顯示所有人員進行「新增、編輯、刪除、批量操作」的歷史紀錄。")
                with get_db() as conn:
                    df_prod_logs = pd.read_sql("SELECT timestamp as 操作時間, operator as 操作人員, action_type as 動作類別, details as 變動詳情說明 FROM product_logs ORDER BY id DESC", conn)
                    
                if df_prod_logs.empty:
                    st.caption("✨ 目前尚無任何商品更動日誌紀錄。")
                else:
                    st.dataframe(df_prod_logs, use_container_width=True, hide_index=True)
                    st.write("")
                    if st.checkbox("⚠️ 啟用清除歷史日誌安全授權"):
                        if st.button("🗑️ 清空所有商品變更日誌紀錄", type="primary"):
                            with get_db() as conn:
                                conn.execute("DELETE FROM product_logs")
                                conn.commit()
                            st.success("日誌紀錄已清空。")
                            time.sleep(1)
                            st.rerun()
    else:
        st.error("🚫 您無權限訪問此模組")

elif menu == "商品庫存":
    st.title("🏭 商品庫存與物料倉庫管理")
    current_operator = st.session_state.get('user', 'admin')
    is_admin = (st.session_state.get('role') == 'Admin')

    with get_db() as conn:
        rate = conn.execute("SELECT value FROM settings WHERE key='exchange_rate'").fetchone()[0]
        wh_df = pd.read_sql("SELECT name FROM warehouses", conn)
        wh_list = wh_df['name'].tolist()
        prod_df = pd.read_sql("SELECT 編碼 FROM products ORDER BY 編碼 ASC", conn)
        all_products = prod_df['編碼'].tolist()
    
    new_rate = st.sidebar.number_input("當前人民幣匯率 (RMB to TWD)", value=rate, step=0.01)
    if st.sidebar.button("更新匯率"):
        with get_db() as conn:
            conn.execute("UPDATE settings SET value=? WHERE key='exchange_rate'", (new_rate,))
            conn.commit()
        st.rerun()

    if check_perm(role, "商品庫存", "can_view"):
        # 🌟 動態隱藏分頁
        tabs_list = ["📊 庫存數據總覽", "🛠️ 庫存批次明細維護 (編輯/刪除)", "🏢 倉庫位置管理"]
        if is_admin:
            tabs_list.append("📜 歷史異動軌跡日誌 (僅管理員可見)")
            
        tabs = st.tabs(tabs_list)
        
        with tabs[0]:
            c_wh, c_status = st.columns(2)
            selected_wh = c_wh.selectbox("🔍 篩選特定分倉庫存", ["所有倉庫"] + wh_list, key="inv_wh_filter")
            show_type = c_status.radio("依庫存水位篩選", ["顯示所有", "僅顯示有庫存", "僅顯示缺貨"], horizontal=True, key="inv_status_filter")
            
            with get_db() as conn:
                query = """
                SELECT p.圖片路徑, p.編碼, p.名稱, p.類別, p.品牌, 
                       COALESCE(SUM(i.數量), 0) as 總庫存, 
                       COALESCE(SUM(i.採購金額_RMB), 0) as "總採購金額_RMB", 
                       AVG(i.單支成本_RMB) as "平均成本_RMB"
                FROM products p LEFT JOIN inventory i ON p.編碼 = i.編碼
                """
                params = []
                if selected_wh != "所有倉庫":
                    query += " AND i.倉庫位置 = ?"
                    params.append(selected_wh)
                query += " GROUP BY p.編碼 ORDER BY p.編碼 ASC"
                df = pd.read_sql(query, conn, params=params)
                
                wh_query = "SELECT 編碼, 倉庫位置, SUM(數量) as 數量 FROM inventory GROUP BY 編碼, 倉庫位置"
                df_wh = pd.read_sql(wh_query, conn)
                if not df_wh.empty:
                    wh_pivot = df_wh.pivot_table(index='編碼', columns='倉庫位置', values='數量', aggfunc='sum').fillna(0).astype(int)
                    df = df.merge(wh_pivot, on='編碼', how='left')
                    wh_cols = list(wh_pivot.columns)
                    for c in wh_cols: df[c] = df[c].fillna(0).astype(int)
                else:
                    wh_cols = []
            
            df["總庫存金額_RMB"] = df["總採購金額_RMB"]
            df["總庫存金額_TWD"] = df["總庫存金額_RMB"] * new_rate
            df["平均成本_TWD"] = df["平均成本_RMB"] * new_rate
            
            def get_image_base64(path):
                if pd.isna(path) or not path: return None
                if os.path.exists(path):
                    with open(path, "rb") as f: return f"data:image/jpeg;base64,{base64.b64encode(f.read()).decode('utf-8')}"
                return None
            df['商品圖片'] = df['圖片路徑'].apply(get_image_base64)
            
            cols = ['商品圖片', '編碼', '名稱', '類別', '品牌', '總庫存'] + wh_cols + ['平均成本_RMB', '平均成本_TWD', '總庫存金額_RMB', '總庫存金額_TWD']
            filtered_df = df[cols].copy()
            if show_type == "僅顯示有庫存": filtered_df = filtered_df[filtered_df["總庫存"] > 0]
            elif show_type == "僅顯示缺貨": filtered_df = filtered_df[filtered_df["總庫存"] <= 0]
            
            col_cfg = {
                "商品圖片": st.column_config.ImageColumn("圖片"),
                "總庫存": st.column_config.NumberColumn("🔥 總計", format="%d 支"),
                "平均成本_RMB": st.column_config.NumberColumn("單支成本 (¥)", format="¥ %.2f"),
                "平均成本_TWD": st.column_config.NumberColumn("單支成本 (NT$)", format="$ %.2f")
            }
            for w in wh_cols: col_cfg[w] = st.column_config.NumberColumn(f"📍 {w}", format="%d")
            
            st.dataframe(filtered_df, use_container_width=True, hide_index=True, column_config=col_cfg)
            
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                filtered_df.drop(columns=['商品圖片']).to_excel(writer, index=False, sheet_name='Inventory')
            
            if check_perm(role, "商品庫存", "can_download"):
                st.download_button("💾 下載當前篩選庫存報表", data=output.getvalue(), file_name=f"inventory_{selected_wh}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.caption("🔒 您沒有下載庫存報表的權限。")

        with tabs[1]:
            st.subheader("🛠️ 原始進貨批次明細修正區")
            if not check_perm(role, "商品庫存", "can_edit"):
                st.warning("🔒 您的權限僅能查看明細，無法執行修正或刪除作業。")
            else:
                st.write("不論是手動匯入或是由採購單點收進來的個別紀錄，皆會在下方展開。您可以選取對應的序號進行精準修正或刪除。")
                with get_db() as conn:
                    df_raw_inv = pd.read_sql('SELECT i.id as 流水號, i.編碼, p.名稱 as 商品名稱, i.倉庫位置, i.數量, i.單支成本_RMB as "單支成本(RMB)", i.採購廠商, i.進貨日期 FROM inventory i LEFT JOIN products p ON i.編碼 = p.編碼 ORDER BY i.id DESC', conn)
                    
                if df_raw_inv.empty:
                    st.info("目前庫存流水表中無任何原始資料。")
                else:
                    st.dataframe(df_raw_inv, use_container_width=True, hide_index=True)
                    st.divider()
                    
                    st.markdown("#### ✍️ 執行特定批次庫存更正作業")
                    select_id = st.selectbox("請指定您要修正或刪除的庫存「流水號 (ID)」：", ["請選擇 ID..."] + df_raw_inv['流水號'].tolist())
                    
                    if select_id != "請選擇 ID...":
                        old_row = df_raw_inv[df_raw_inv['流水號'] == select_id].iloc[0]
                        with st.form(f"edit_inventory_form_{select_id}"):
                            st.info(f"正在維護流水號 ID: {select_id} ｜ 原品項：{old_row['編碼']} - {old_row['商品名稱']}")
                            m_c1, m_c2 = st.columns(2)
                            edit_code = m_c1.selectbox("更正商品編碼", all_products, index=all_products.index(old_row['編碼']) if old_row['編碼'] in all_products else 0)
                            edit_wh = m_c2.selectbox("更正存放倉庫位置", wh_list, index=wh_list.index(old_row['倉庫位置']) if old_row['倉庫位置'] in wh_list else 0)
                            
                            m_c3, m_c4, m_c5 = st.columns(3)
                            edit_qty = m_c3.number_input("修正後數量", min_value=0, step=1, value=int(old_row['數量']))
                            edit_cost = m_c4.number_input("修正後人民幣單價", min_value=0.0, step=0.1, value=float(old_row['單支成本(RMB)']))
                            edit_vendor = m_c5.text_input("更正採購廠商", value=str(old_row['採購廠商']))
                            edit_date = st.date_input("修正進貨日期", value=pd.to_datetime(old_row['進貨日期']))
                            
                            col_btn1, col_btn2 = st.columns(2)
                            save_submit = col_btn1.form_submit_button("💾 儲存此筆更正變更", type="primary", use_container_width=True)
                            delete_submit = col_btn2.form_submit_button("🗑️ 徹底刪除此筆庫存紀錄", use_container_width=True)
                            
                            if save_submit:
                                calc_amt_rmb = edit_qty * edit_cost
                                try:
                                    with get_db() as conn:
                                        conn.execute("UPDATE inventory SET 編碼=?, 倉庫位置=?, 數量=?, 單支成本_RMB=?, 採購廠商=?, 採購金額_RMB=?, 進貨日期=? WHERE id=?", (edit_code, edit_wh, edit_qty, edit_cost, edit_vendor.strip(), calc_amt_rmb, str(edit_date), select_id))
                                        conn.commit()
                                    log_details = f"修改流水號 {select_id}。原資料:[品項:{old_row['編碼']},數量:{old_row['數量']},倉:{old_row['倉庫位置']}] ➡️ 新資料:[品項:{edit_code},數量:{edit_qty},倉:{edit_wh},單價:{edit_cost} RMB]"
                                    log_inventory_change(current_operator, "修正庫存", log_details)
                                    st.success(f"✅ 流水號 【{select_id}】 庫存明細更正成功！")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 修正失敗：{e}")
                                    
                            if delete_submit:
                                try:
                                    with get_db() as conn:
                                        conn.execute("DELETE FROM inventory WHERE id=?", (select_id,))
                                        conn.commit()
                                    log_details = f"徹底刪除流水號 {select_id} 紀錄。原內含品項:{old_row['編碼']}, 移除數量:{old_row['數量']} 支, 原倉庫:{old_row['倉庫位置']}, 廠商:{old_row['採購廠商']}"
                                    log_inventory_change(current_operator, "刪除庫存", log_details)
                                    st.success(f"🗑️ 庫存流水號 【{select_id}】 已成功從資料庫中移除！")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 刪除動作失敗：{e}")

        with tabs[2]:
            st.subheader("🏢 系統倉庫位置管理")
            with get_db() as conn:
                df_wh_edit = pd.read_sql("SELECT name as 倉庫名稱 FROM warehouses", conn)
                
            can_edit_wh = check_perm(role, "商品庫存", "can_edit")
            edited_wh = st.data_editor(
                df_wh_edit, num_rows="dynamic" if can_edit_wh else "fixed", use_container_width=True,
                disabled=not can_edit_wh,
                column_config={"倉庫名稱": st.column_config.TextColumn("📦 倉庫名稱 (必填，不可重複)", required=True)}
            )
            
            if can_edit_wh:
                if st.button("💾 儲存所有倉庫設定", type="primary"):
                    current_whs = [w.strip() for w in edited_wh['倉庫名稱'].dropna().astype(str).tolist() if w.strip() != '']
                    if not current_whs:
                        st.error("❌ 系統至少需要保留一個倉庫！")
                    else:
                        try:
                            with get_db() as conn:
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM warehouses")
                                for w in current_whs: cursor.execute("INSERT INTO warehouses (name) VALUES (?)", (w,))
                                conn.commit()
                            st.success("✅ 倉庫名單已成功更新！系統將自動重載。")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 儲存失敗：{str(e)}")
            else:
                st.caption("🔒 您沒有編輯倉庫名稱的權限。")

        # 🌟 僅有 Admin 能觀看的庫存異動日誌
        if is_admin:
            with tabs[3]:
                st.subheader("📜 庫存操作變動審查軌跡 (Admin 專屬)")
                st.write("此處會即時顯示系統中所有人工進行「修正庫存」或「刪除庫存」的歷史操作紀錄，時間依最新時間排序。")
                with get_db() as conn:
                    df_logs = pd.read_sql("SELECT timestamp as 操作時間, operator as 操作人員, action_type as 動作類別, details as 變動詳情說明 FROM inventory_logs ORDER BY id DESC", conn)
                    
                if df_logs.empty:
                    st.caption("✨ 目前尚無任何庫存更動日誌紀錄，系統營運正常。")
                else:
                    st.dataframe(df_logs, use_container_width=True, hide_index=True)
                    st.write("")
                    if st.checkbox("⚠️ 啟用清除歷史日誌安全授權 (僅限 Admin)"):
                        if st.button("🗑️ 清空所有變更日誌歷史紀錄", type="primary"):
                            with get_db() as conn:
                                conn.execute("DELETE FROM inventory_logs")
                                conn.commit()
                            st.success("日誌紀錄已清空。")
                            time.sleep(1)
                            st.rerun()
    else:
        st.error("🚫 您無權限訪問此模組")

elif menu == "採購管理":
    st.title("🛒 採購與進貨管理系統")
    current_operator = st.session_state.get('user', 'admin')
    is_admin = (st.session_state.get('role') == 'Admin')
    
    if not check_perm(role, "採購管理", "can_view"):
        st.error("🚫 您無權限訪問此模組")
        st.stop()

    with get_db() as conn:
        rate = conn.execute("SELECT value FROM settings WHERE key='exchange_rate'").fetchone()[0]

    # 🌟 動態隱藏分頁
    tabs_list = ["📝 新增採購單", "📋 採購單歷史與點收驗收", "📊 批次作業 (導入/導出)"]
    if is_admin:
        tabs_list.append("📜 採購異動日誌 (僅管理員可見)")
        
    tabs = st.tabs(tabs_list)

    with tabs[0]:
        st.subheader("✍️ 建立新採購單單據")
        if not check_perm(role, "採購管理", "can_edit"):
            st.warning("🔒 您的權限無法新增採購單。")
        else:
            with get_db() as conn:
                prod_df = pd.read_sql("SELECT 編碼, 名稱, 圖片路徑 FROM products ORDER BY 編碼 ASC", conn)
                wh_df = pd.read_sql("SELECT name FROM warehouses", conn) 
                
            prod_df['顯示選單'] = prod_df['編碼'] + " | " + prod_df['名稱']
            valid_product_options = prod_df['顯示選單'].tolist()
            valid_warehouses = wh_df['name'].tolist() 
            
            if not valid_product_options:
                st.warning("⚠️ 目前商品訊息庫中沒有任何商品資料，請先至『商品訊息』建立基本商品再進行採購。")
            elif not valid_warehouses:
                st.warning("⚠️ 系統偵測不到任何倉庫！請先至『商品庫存』分頁建立至少一個倉庫位置。")
            else:
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                date_input = col_m1.date_input("採購日期")
                supplier_input = col_m2.text_input("採購廠商 (供應商名稱)", placeholder="例如：法國香氛總倉")
                warehouse_input = col_m3.selectbox("購入的倉庫", valid_warehouses)
                staff_input = col_m4.text_input("採購人員", value=current_operator)
                
                st.write("📌 **請於下方表格中挑選採購品項及金額：**")
                if "po_editor_df_v2" not in st.session_state:
                    st.session_state.po_editor_df_v2 = pd.DataFrame(columns=["挑選商品", "數量", "人民幣單價"])
                    
                edited_items = st.data_editor(
                    st.session_state.po_editor_df_v2, num_rows="dynamic", use_container_width=True, key="po_items_editor_v2",
                    column_config={
                        "挑選商品": st.column_config.SelectboxColumn("📦 選擇商品 (編碼 | 名稱)", options=valid_product_options, required=True),
                        "數量": st.column_config.NumberColumn("🔢 採購數量", min_value=1, step=1, default=1),
                        "人民幣單價": st.column_config.NumberColumn("💰 人民幣單價 (RMB)", min_value=0.0, step=0.01, default=0.0)
                    }
                )
                
                if not edited_items.empty and not edited_items["挑選商品"].isnull().all():
                    st.write("🖼️ **已選商品圖片確認區** (預防選錯防呆)")
                    preview_cols = st.columns(6)
                    col_idx = 0
                    for _, row in edited_items.iterrows():
                        if pd.notna(row['挑選商品']) and str(row['挑選商品']).strip():
                            raw_code = str(row['挑選商品']).split(" | ")[0].strip()
                            matching_row = prod_df[prod_df['編碼'] == raw_code]
                            if not matching_row.empty:
                                img_path = matching_row['圖片路徑'].values[0]
                                with preview_cols[col_idx % 6]:
                                    st.markdown(f"<div style='text-align:center; font-size:14px; font-weight:bold;'>{raw_code}</div>", unsafe_allow_html=True)
                                    if img_path and os.path.exists(img_path):
                                        st.image(img_path, use_container_width=True)
                                    else:
                                        st.info("無圖片")
                                col_idx += 1
                    st.write("") 
                    
                if not edited_items.empty:
                    edited_items['數量'] = pd.to_numeric(edited_items['數量']).fillna(0).astype(int)
                    edited_items['人民幣單價'] = pd.to_numeric(edited_items['人民幣單價']).fillna(0.0)
                    edited_items['總金額_RMB'] = edited_items['數量'] * edited_items['人民幣單價']
                    
                    total_qty = int(edited_items['數量'].sum())
                    total_rmb = float(edited_items['總金額_RMB'].sum())
                    total_twd = total_rmb * rate
                else:
                    total_qty, total_rmb, total_twd = 0, 0.0, 0.0
                    
                st.divider()
                sum_c1, sum_c2, sum_c3 = st.columns(3)
                sum_c1.metric("📦 總採購數量", f"{total_qty} 支")
                sum_c2.metric("¥ 人民幣總金額", f"{total_rmb:,.2f} RMB")
                sum_c3.metric("$ 台幣總金額 (自動換算)", f"{total_twd:,.2f} TWD", f"目前匯率: {rate}")
                
                if st.button("🚀 提交並儲存此採購單", type="primary", use_container_width=True):
                    if not supplier_input.strip():
                        st.error("❌ 儲存失敗：採購廠商為必填項目，請勿留空！")
                    elif edited_items.empty or total_qty == 0:
                        st.error("❌ 儲存失敗：採購單內必須包含至少一項商品且數量大於 0！")
                    else:
                        try:
                            order_id = f"PO-{time.strftime('%Y%m%d')}-{int(time.time())%100000:05d}"
                            with get_db() as conn:
                                cursor = conn.cursor()
                                cursor.execute("INSERT INTO procurement_orders (order_id, date, supplier, total_qty, total_amount_rmb, total_amount_twd, warehouse, staff, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '待驗收')", 
                                               (order_id, str(date_input), supplier_input.strip(), total_qty, total_rmb, total_twd, warehouse_input, staff_input))
                                
                                for _, row in edited_items.iterrows():
                                    if pd.notna(row['挑選商品']) and str(row['挑選商品']).strip() and row['數量'] > 0:
                                        raw_code = str(row['挑選商品']).split(" | ")[0].strip()
                                        item_total_rmb = int(row['數量']) * float(row['人民幣單價'])
                                        cursor.execute("INSERT INTO procurement_items (order_id, code, qty, unit_price_rmb, total_price_rmb) VALUES (?, ?, ?, ?, ?)", 
                                                       (order_id, raw_code, int(row['數量']), float(row['人民幣單價']), item_total_rmb))
                                conn.commit()
                            
                            # 🌟 寫入日誌
                            log_system_action("採購管理", current_operator, "建立採購單", f"單號: {order_id}，廠商: {supplier_input}，共 {total_qty} 件，金額 {total_rmb:,.2f} RMB")
                                
                            st.success(f"✅ 採購單 【{order_id}】 建立並保存成功！請至核對頁面辦理點收。")
                            st.session_state.po_editor_df_v2 = pd.DataFrame(columns=["挑選商品", "數量", "人民幣單價"]) 
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 資料庫寫入異常，單據儲存失敗！錯誤詳情：{str(e)}")

    with tabs[1]:
        st.subheader("📋 採購單據維護與點收庫存作業")
        with get_db() as conn:
            df_orders = pd.read_sql("SELECT order_id as 採購單號, date as 日期, supplier as 廠商, total_qty as 總數量, total_amount_rmb as 人民幣總額, total_amount_twd as 台幣總額, warehouse as 購入倉庫, staff as 採購人員, status as 狀態 FROM procurement_orders ORDER BY 日期 DESC, order_id DESC", conn)
            
        if df_orders.empty:
            st.info("目前系統中無任何採購歷史紀錄。")
        else:
            st.dataframe(df_orders, use_container_width=True, hide_index=True)
            st.divider()
            
            selected_po = st.selectbox("🔍 請選取採購單號以展開「詳細明細內容」與辦理進貨點收入庫：", df_orders['採購單號'].tolist())
            if selected_po:
                order_meta = df_orders[df_orders['採購單號'] == selected_po].iloc[0]
                with get_db() as conn:
                    df_items = pd.read_sql("SELECT i.code as 編碼, p.名稱 as 名稱, p.圖片路徑, i.qty as 數量, i.unit_price_rmb as 單價, i.total_price_rmb as 總金額 FROM procurement_items i LEFT JOIN products p ON i.code = p.編碼 WHERE i.order_id = ?", conn, params=(selected_po,))
                    
                st.write(f"📁 **採購單號：** `{selected_po}` ｜ **狀態：** `{order_meta['狀態']}` ｜ **目的地倉庫：** `{order_meta['購入倉庫']}`")
                
                for _, item in df_items.iterrows():
                    with st.container(border=True):
                        img_c, details_c = st.columns([1.2, 6])
                        if item['圖片路徑'] and os.path.exists(item['圖片路徑']):
                            img_c.image(item['圖片路徑'], width=90)
                        else:
                            img_c.write("無商品圖片")
                            
                        details_c.markdown(
                            f"🆔 **商品編碼**：`{item['編碼']}`  &nbsp;&nbsp;&nbsp;&nbsp; 📦 **商品名稱**：**{item['名稱']}**\n\n"
                            f"🔢 **採購數量**：`{item['數量']}` 支 ｜ 💰 **人民幣單價**：`{item['單價']}` RMB ｜ 🧾 **項目總金額**：`{item['總金額']}` RMB"
                        )
                        
                if order_meta['狀態'] == '待驗收':
                    st.write("")
                    if check_perm(role, "採購管理", "can_edit"):
                        # 🌟 新增：將按鈕拆分為左右兩欄 (7:3 比例)
                        c_recv, c_del = st.columns([7, 3])
                        
                        if c_recv.button(f"🚚 點收完成！確認將單號 {selected_po} 的商品數量正式撥入『商品庫存』", type="primary", use_container_width=True):
                            try:
                                with get_db() as conn:
                                    cursor = conn.cursor()
                                    for _, item in df_items.iterrows():
                                        cursor.execute("INSERT INTO inventory (編碼, 倉庫位置, 數量, 單支成本_RMB, 採購廠商, 採購金額_RMB, 進貨日期) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                                                       (item['編碼'], order_meta['購入倉庫'], item['數量'], item['單價'], order_meta['廠商'], item['總金額'], order_meta['日期']))
                                    cursor.execute("UPDATE procurement_orders SET status = '已入庫' WHERE order_id = ?", (selected_po,))
                                    conn.commit()
                                
                                # 🌟 寫入日誌
                                log_system_action("採購管理", current_operator, "點收入庫", f"單號: {selected_po} 已成功驗收，並撥入倉庫 {order_meta['購入倉庫']}")
                                
                                st.success(f"✅ 點收入庫成功！採購單 {selected_po} 已正式與庫存完成連動，數量已匯入庫存。")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 庫存撥配連動過程中發生異常錯誤：{str(e)}")
                                
                        # 🌟 新增：刪除待驗收採購單的按鈕與邏輯
                        if c_del.button("🗑️ 刪除此採購單", use_container_width=True):
                            try:
                                with get_db() as conn:
                                    conn.execute("DELETE FROM procurement_orders WHERE order_id = ?", (selected_po,))
                                    conn.execute("DELETE FROM procurement_items WHERE order_id = ?", (selected_po,))
                                    conn.commit()
                                log_system_action("採購管理", current_operator, "刪除採購單", f"刪除了尚未驗收的採購單: {selected_po}")
                                st.success(f"🗑️ 採購單 {selected_po} 已成功刪除！")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 刪除失敗：{str(e)}")
                    else:
                        st.warning("🔒 您的權限僅能查看明細，無法執行點收入庫或刪除作業。")
                else:
                    st.write("")
                    st.success("🎉 此採購單已完成點收入庫驗收，商品數量已在『商品庫存管理』核算中。")
                    
                    # 🌟 新增：允許刪除已入庫的歷史紀錄，但給予防呆提示
                    if check_perm(role, "採購管理", "can_edit"):
                        if st.button("🗑️ 刪除此歷史採購單紀錄", use_container_width=True):
                            try:
                                with get_db() as conn:
                                    conn.execute("DELETE FROM procurement_orders WHERE order_id = ?", (selected_po,))
                                    conn.execute("DELETE FROM procurement_items WHERE order_id = ?", (selected_po,))
                                    conn.commit()
                                log_system_action("採購管理", current_operator, "刪除歷史採購單", f"刪除了已入庫的歷史採購單: {selected_po}")
                                st.success(f"🗑️ 歷史採購單 {selected_po} 已成功刪除！(⚠️ 提醒：這不會影響已經撥入庫存的商品數量)")
                                time.sleep(2)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 刪除失敗：{str(e)}")
                                
    with tabs[2]:
        st.subheader("📤 導出公司完整採購報表")
        if not check_perm(role, "採購管理", "can_download"):
            st.warning("🔒 您沒有下載採購報表的權限。")
        else:
            try:
                with get_db() as conn:
                    df_report = pd.read_sql("SELECT o.order_id as 採購單號, o.date as 日期, o.supplier as 廠商, o.warehouse as 購入倉庫, o.staff as 採購人員, o.status as 狀態, i.code as 商品編碼, i.qty as 採購數量, i.unit_price_rmb as 人民幣單價, i.total_price_rmb as 人民幣總額 FROM procurement_orders o JOIN procurement_items i ON o.order_id = i.order_id ORDER BY o.date DESC, o.order_id DESC", conn)
                from io import BytesIO
                output_excel = BytesIO()
                with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                    df_report.to_excel(writer, index=False, sheet_name='採購明細總表')
                st.download_button(label="💾 點擊下載完整採購歷史明細報表 (Excel 格式)", data=output_excel.getvalue(), file_name="procurement_global_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            except Exception as e:
                st.error(f"❌ 報表導出模組發生例外錯誤：{str(e)}")

        st.divider()
        st.subheader("📥 導入外部採購單資料")
        if not check_perm(role, "採購管理", "can_upload"):
            st.warning("🔒 您沒有上傳外部採購單的權限。")
        else:
            st.caption("💡 批次匯入 Excel / CSV 欄位名稱順序必須包含：日期, 廠商, 購入倉庫, 採購人員, 商品編碼, 數量, 人民幣單價")
            uploaded_po = st.file_uploader("選擇您要上傳的批次採購檔案", type=["csv", "xlsx"])
            if uploaded_po and st.button("🚀 執行批量採購單據匯入作業", type="primary"):
                try:
                    df_imp = pd.read_csv(uploaded_po) if uploaded_po.name.endswith('.csv') else pd.read_excel(uploaded_po, engine='openpyxl')
                    required_cols = ["日期", "廠商", "購入倉庫", "採購人員", "商品編碼", "數量", "人民幣單價"]
                    
                    if not all(c in df_imp.columns for c in required_cols):
                        st.error(f"❌ 匯入失敗：檔案內必填欄位不符，必須完整包含：{required_cols}")
                    else:
                        df_imp['Group_Key'] = df_imp['日期'].astype(str) + "_" + df_imp['廠商'].astype(str) + "_" + df_imp['購入倉庫'].astype(str)
                        with get_db() as conn:
                            cursor = conn.cursor()
                            for g_key, group in df_imp.groupby('Group_Key'):
                                base_row = group.iloc[0]
                                order_id = f"PO-IMP-{time.strftime('%Y%m%d')}-{int(time.time())%100000:05d}"
                                time.sleep(0.02)
                                
                                g_qty = int(group['數量'].sum())
                                g_rmb = float((group['數量'] * group['人民幣單價']).sum())
                                g_twd = g_rmb * rate
                                
                                cursor.execute("INSERT INTO procurement_orders (order_id, date, supplier, total_qty, total_amount_rmb, total_amount_twd, warehouse, staff, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '待驗收')", 
                                               (order_id, str(base_row['日期']), str(base_row['廠商']), g_qty, g_rmb, g_twd, str(base_row['購入倉庫']), str(base_row['採購人員'])))
                                
                                for _, row in group.iterrows():
                                    item_rmb = int(row['數量']) * float(row['人民幣單價'])
                                    cursor.execute("INSERT INTO procurement_items (order_id, code, qty, unit_price_rmb, total_price_rmb) VALUES (?, ?, ?, ?, ?)", 
                                                   (order_id, str(row['商品編碼']), int(row['數量']), float(row['人民幣單價']), item_rmb))
                            conn.commit()
                        
                        # 🌟 寫入日誌
                        log_system_action("採購管理", current_operator, "批次匯入採購單", f"從 Excel/CSV 成功匯入外部單據")
                            
                        st.success("✅ 外部採購單據批次匯入作業成功完成！所有新單據預設為『待驗收』狀態。")
                        time.sleep(1.5)
                        st.rerun()
                except Exception as e:
                    st.error(f"❌ 批量解析匯入失敗：格式不正確或資料有誤。詳情：{str(e)}")

    # 🌟 僅 Admin 可見的採購日誌分頁
    if is_admin:
        with tabs[3]:
            st.subheader("📜 採購管理日誌 (Admin 專屬)")
            st.write("顯示新增採購單、點收入庫、匯入等所有操作歷史。")
            with get_db() as conn:
                df_sys_logs = pd.read_sql("SELECT timestamp as 操作時間, operator as 操作人員, action_type as 動作類別, details as 變動詳情說明 FROM system_logs WHERE module='採購管理' ORDER BY id DESC", conn)
                
            if df_sys_logs.empty:
                st.caption("✨ 目前尚無採購紀錄日誌。")
            else:
                st.dataframe(df_sys_logs, use_container_width=True, hide_index=True)
                
elif menu == "訂單明細":
    st.title("🧾 客戶訂單明細")
    current_operator = st.session_state.get('user', 'admin')
    
    if not check_perm(role, "訂單明細", "can_view"):
        st.error("🚫 您無權限訪問此模組")
        st.stop()

    # 🌟 系統熱更新：確保 customer_orders 表格擁有獨立的「物流運費_RMB」欄位，讓人民幣原價永久保存
    with get_db() as conn:
        cursor = conn.cursor()
        
        # ⚠️ PostgreSQL 專屬寫法：查詢系統表來確認欄位是否存在
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'customer_orders'")
        # 由於 PostgreSQL 預設會將未加引號的欄位名稱轉為小寫，這裡統一轉小寫來比對防呆
        cols = [info[0].lower() for info in cursor.fetchall()]
        
        if '物流運費_rmb' not in cols:
            cursor.execute("ALTER TABLE customer_orders ADD COLUMN 物流運費_RMB REAL DEFAULT 0.0")
            # 根據現有台幣運費反推初始的人民幣並存入 (僅執行一次)
            rate_val = cursor.execute("SELECT value FROM settings WHERE key='exchange_rate'").fetchone()[0]
            cursor.execute("UPDATE customer_orders SET 物流運費_RMB = 物流運費 / ? WHERE 物流運費 > 0", (rate_val,))
            conn.commit()

        # 👇👇👇 請把這段插入在這裡：升級資料庫的日期欄位型態 👇👇👇
        try:
            cursor.execute("SELECT data_type FROM information_schema.columns WHERE table_name = 'customer_orders' AND column_name = '訂單日期'")
            dt_type = cursor.fetchone()
            # 如果發現它還是純 DATE，就強制升級成 TIMESTAMP (包含時間)
            if dt_type and dt_type[0].lower() == 'date':
                cursor.execute("ALTER TABLE customer_orders ALTER COLUMN 訂單日期 TYPE TIMESTAMP USING 訂單日期::TIMESTAMP")
                conn.commit()
        except:
            conn.rollback() # 防呆機制
        # 👆👆👆 插入結束 👆👆👆

        rate = cursor.execute("SELECT value FROM settings WHERE key='exchange_rate'").fetchone()[0]

    new_rate = st.sidebar.number_input("當前人民幣匯率 (RMB to TWD)", value=rate, step=0.01, key="order_sidebar_rate")
    if st.sidebar.button("更新匯率", key="btn_update_order_rate"):
        with get_db() as conn:
            conn.execute("UPDATE settings SET value=? WHERE key='exchange_rate'", (new_rate,))
            # 🌟 核心修正：自動根據新的匯率，重新核算所有訂單的台幣運費、出貨總成本與損益！(保留原本的 RMB 運費完全不變)
            conn.execute("""
                UPDATE customer_orders 
                SET 物流運費 = 物流運費_RMB * ?,
                    出貨成本 = 商品成本 + (物流運費_RMB * ?),
                    訂單損益 = 包裹應收 - (商品成本 + (物流運費_RMB * ?))
                WHERE 物流運費_RMB > 0
            """, (new_rate, new_rate, new_rate))
            conn.commit()
        st.toast(f"✅ 匯率已更新為 {new_rate}！系統已自動幫您重新核算所有訂單的台幣運費與利潤。")
        time.sleep(1.5)
        st.rerun()

    # 🌟 1. 取得資料庫資料
    with get_db() as conn:
        df_orders = pd.read_sql("SELECT * FROM customer_orders ORDER BY 訂單日期 DESC", conn)
        # 👇 新增這行：撈取商品資料庫來做翻譯比對
        df_prods = pd.read_sql("SELECT 編碼, 品牌, 名稱 FROM products", conn)

    # 🌟 終極防呆：處理 PostgreSQL 自動轉小寫問題，若無欄位則強制建立
    if not df_orders.empty:
        if '物流運費_rmb' in df_orders.columns:
            df_orders = df_orders.rename(columns={'物流運費_rmb': '物流運費_RMB'})
        if '物流運費_RMB' not in df_orders.columns:
            df_orders['物流運費_RMB'] = 0.0

    # 🌟 2. 資料預處理與重複客偵測
    if not df_orders.empty:
        # 防呆補空值
        df_orders['姓名'] = df_orders['姓名'].fillna('').astype(str)
        df_orders['電話'] = df_orders['電話'].fillna('').astype(str)
        df_orders['信箱'] = df_orders['信箱'].fillna('').astype(str)
        df_orders['顧客備註'] = df_orders['顧客備註'].fillna('').astype(str)
        df_orders['商家備註'] = df_orders['商家備註'].fillna('').astype(str)

        # 電話與店號自動補 0
        def fix_phone(val):
            s = str(val).replace('.0', '').strip()
            if s and s not in ['nan', 'None', '']: return '0' + s if not s.startswith('0') else s
            return ""

        def fix_store_id(row):
            s = str(row['店號']).replace('.0', '').strip()
            if s and s not in ['nan', 'None', '']:
                if '全家' in str(row['門市']) and not s.startswith('0'): return '0' + s
                return s
            return ""

        df_orders['電話'] = df_orders['電話'].apply(fix_phone)
        df_orders['店號'] = df_orders.apply(fix_store_id, axis=1)

        # 👇 核心新增：建立商品編碼對應字典與翻譯函數
        prod_map = {}
        for _, r in df_prods.iterrows():
            c = str(r['編碼']).strip()
            if c:
                # 只抓取「名稱」欄位，不組合「品牌」，避免疊字重複
                n = str(r['名稱']).strip() if pd.notna(r['名稱']) else ""
                prod_map[c] = n
                
        # 依編碼長度由長到短排序，避免短編碼錯誤蓋掉長編碼的一部分 (例如 P02 被 P02B 蓋過)
        sorted_codes = sorted(prod_map.keys(), key=len, reverse=True)

        def translate_items(text):
            res = str(text) if pd.notna(text) else ""
            if not res or res.strip() in ['nan', 'None']: return ""
            for code in sorted_codes:
                if code in res:
                    # 執行精準替換
                    res = res.replace(code, prod_map[code])
            return res
        # 👆 新增結束

        def clean_and_preview(val):
            if pd.isna(val) or str(val).strip() in ['nan', 'None']: return ""
            return str(val)
        df_orders['品項內容_原始'] = df_orders['品項內容'].apply(clean_and_preview)
        
        # 👇 變更：產生翻譯後的品項內容，並用於主表格預覽顯示
        df_orders['品項翻譯'] = df_orders['品項內容_原始'].apply(translate_items)
        df_orders['品項預覽'] = df_orders['品項翻譯'].apply(lambda x: x.replace('\n', ' ｜ '))
        # 👆 變更結束
        
        # 確保財務欄位為數值型態 (加上防呆檢查：欄位存在才進行轉換)
        for col in ['包裹應收', '商品成本', '物流運費', '物流運費_RMB', '出貨成本', '訂單損益']:
            if col in df_orders.columns:
                df_orders[col] = pd.to_numeric(df_orders[col], errors='coerce').fillna(0.0)

        # 👇 智能重複客偵測邏輯 (只要姓名、電話或信箱其一重複大於1次，就標記)
        name_counts = df_orders[df_orders['姓名'] != '']['姓名'].value_counts()
        phone_counts = df_orders[df_orders['電話'] != '']['電話'].value_counts()
        email_counts = df_orders[df_orders['信箱'] != '']['信箱'].value_counts()

        def check_repeat(row):
            if row['姓名'] and name_counts.get(row['姓名'], 0) > 1: return True
            if row['電話'] and phone_counts.get(row['電話'], 0) > 1: return True
            if row['信箱'] and email_counts.get(row['信箱'], 0) > 1: return True
            return False

        df_orders['is_repeat'] = df_orders.apply(check_repeat, axis=1)

    # 🌟 3. 營運數據看板
    st.subheader("📊 營運數據看板")
    c_time, c_custom = st.columns([1, 2])
    # 👇 這裡新增了「本週」選項
    time_filter = c_time.selectbox("📅 選擇統計區間", ["全部", "今日", "本週", "本月", "本季", "今年", "自訂區間"])
    
    df_dash = df_orders.copy()
    if not df_dash.empty:
        df_dash['訂單日期_dt'] = pd.to_datetime(df_dash['訂單日期'], errors='coerce')
        now = pd.Timestamp.today()
        
        if time_filter == "今日": 
            df_dash = df_dash[df_dash['訂單日期_dt'].dt.date == now.date()]
        elif time_filter == "本週": 
            # 👇 這裡新增「本週」的判斷邏輯 (依據 ISO 標準，週一到週日為一週)
            current_year = now.isocalendar().year
            current_week = now.isocalendar().week
            df_dash = df_dash[(df_dash['訂單日期_dt'].dt.isocalendar().year == current_year) & (df_dash['訂單日期_dt'].dt.isocalendar().week == current_week)]
        elif time_filter == "本月": 
            df_dash = df_dash[(df_dash['訂單日期_dt'].dt.year == now.year) & (df_dash['訂單日期_dt'].dt.month == now.month)]
        elif time_filter == "本季":
            current_quarter = (now.month - 1) // 3 + 1
            df_dash = df_dash[(df_dash['訂單日期_dt'].dt.year == now.year) & (df_dash['訂單日期_dt'].dt.quarter == current_quarter)]
        elif time_filter == "今年": 
            df_dash = df_dash[df_dash['訂單日期_dt'].dt.year == now.year]
        elif time_filter == "自訂區間":
            import datetime
            
            # 👇 1. 這裡必須先設定好今天的日期與變數，不然下面找不到會報錯！
            today = datetime.datetime.today()
            year_list = list(range(2025, 2030))
            default_year_idx = year_list.index(today.year) if today.year in year_list else 1
            default_month_idx = today.month - 1
            default_day_idx = today.day - 1

            # 建立開始與結束日期的選單
            st.write("🗓️ **請設定日期範圍**")
            
            # 第一列：開始日期 (預設為今天)
            c1, c2, c3 = st.columns(3)
            start_y = c1.selectbox("開始年份", year_list, index=default_year_idx)
            start_m = c2.selectbox("開始月份", list(range(1, 13)), index=default_month_idx)
            start_d = c3.selectbox("開始日期", list(range(1, 32)), index=default_day_idx)
            
            # 第二列：結束日期 (同樣預設為今天)
            c4, c5, c6 = st.columns(3)
            end_y = c4.selectbox("結束年份", year_list, index=default_year_idx)
            end_m = c5.selectbox("結束月份", list(range(1, 13)), index=11) # 預設選12月
            end_d = c6.selectbox("結束日期", list(range(1, 32)), index=30) # 預設選31號
            
            # 轉換為 Timestamp 物件以便比對
            try:
                start_dt = pd.Timestamp(year=start_y, month=start_m, day=start_d)
                end_dt = pd.Timestamp(year=end_y, month=end_m, day=end_d)
                
                if start_dt > end_dt:
                    st.error("❌ 開始日期不能晚於結束日期！")
                else:
                    # 篩選邏輯：包含開始與結束當天
                    df_dash = df_dash[(df_dash['訂單日期_dt'] >= start_dt) & (df_dash['訂單日期_dt'] <= end_dt)]
            except ValueError:
                st.warning("⚠️ 請確認選擇的日期是否合理 (例如：2月沒有30號)")
    
    total_orders = len(df_dash)
    total_revenue = df_dash['包裹應收'].sum() if not df_dash.empty else 0
    total_cost = df_dash['商品成本'].sum() if not df_dash.empty else 0
    total_shipping = df_dash['物流運費'].sum() if not df_dash.empty else 0
    total_est_profit = df_dash['訂單損益'].sum() if not df_dash.empty else 0
    
    # 👇 🌟 更新你指定的狀態對應邏輯
    picked_up = len(df_dash[df_dash['取貨狀態'] == '簽收']) if not df_dash.empty else 0
    # 總退回數：包含 退回、已上架、已重出、客訴
    unclaimed = len(df_dash[df_dash['取貨狀態'].isin(['退回', '已上架', '已重出', '客訴'])]) if not df_dash.empty else 0
    # 未處理訂單：只算 待出貨
    pending = len(df_dash[df_dash['取貨狀態'] == '待出貨']) if not df_dash.empty else 0
    # 總取消數：只算 已取消
    cancelled = len(df_dash[df_dash['取貨狀態'] == '已取消']) if not df_dash.empty else 0
    
    actual_profit = 0
    if not df_dash.empty:
        profit_from_picked = df_dash[df_dash['取貨狀態'] == '簽收']['訂單損益'].sum()
        loss_from_unclaimed = df_dash[df_dash['取貨狀態'] == '退回']['物流運費'].sum()
        actual_profit = profit_from_picked - loss_from_unclaimed

    st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 10px; border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # 第一排：核心營收與利潤 (4個欄位)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 總訂單數", f"{total_orders:,}")
    m2.metric("💰 總營業額", f"${total_revenue:,.0f}")
    m3.metric("📈 總預估利潤", f"${total_est_profit:,.0f}")
    m4.metric("💎 總實際利潤", f"${actual_profit:,.0f}", help="實際利潤 = (簽收的訂單損益) - (退回所損失的物流運費)")
    
    # 增加一點排與排之間的呼吸空間
    st.markdown("<br>", unsafe_allow_html=True) 

    # 第二排：成本與物流狀態 (4個欄位)
    m5, m6, m7, m8 = st.columns(4)
    m5.metric("🛒 總成本", f"${total_cost:,.0f}")
    m6.metric("🚚 總運費", f"${total_shipping:,.0f}")
    m7.metric("✅ 總簽收數", f"{picked_up:,}")
    m8.metric("❌ 總退回數", f"{unclaimed:,}", help="包含：退回、已上架、已重出、客訴")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # 第三排：待處理與取消 (切成 4 格但只放 2 個，維持一致的寬度)
    m9, m10, _1, _2 = st.columns(4)
    m9.metric("⏳ 未處理訂單", f"{pending:,}", help="僅計算狀態為「待出貨」的訂單")
    m10.metric("🚫 總取消數", f"{cancelled:,}")

    st.divider()
    
    can_edit = check_perm(role, "訂單明細", "can_edit")
    
    # 🌟 修改為 3 個 Tab 分頁
    t1, t2, t3 = st.tabs(["📄 訂單總表與追蹤", "✍️ 手動新增單筆", "📥 批量導入與更新"])
    
    # 🌟 共用新的狀態清單
    STATUS_LIST = ["待出貨", "備貨中", "配送中", "已送達待取", "簽收", "退回", "已取消", "客訴", "已上架", "已重出"]

    with t1:
        st.info("💡 **自動防護偵測**：若表格前方的「⚠️ 警示」欄位顯示「🚨 重複」，代表該顧客（依姓名、電話或信箱比對）在系統內有 **2筆以上** 紀錄，方便一眼識別常客或潛在惡意未取顧客。若要查看完整備註與信箱，請開啟上方「展開顯示所有詳細欄位」。")

        if df_orders.empty:
            st.warning("目前尚無任何訂單資料。請至「批次匯入與建檔」上傳 Excel/CSV。")

        # 🌟 修改：還原為 3 欄排版，移除獨立日期篩選，改為與上方「營運數據看板」同步
        c_search, c_status, c_toggle = st.columns([2, 1, 1.2])
        with c_search: search_kw = st.text_input("🔍 搜尋訂單 (輸入姓名、電話、信箱或單號)", "")
        with c_status: status_filter = st.selectbox("📌 狀態篩選", ["全部"] + STATUS_LIST)
        with c_toggle:
            st.write(""); st.write("")
            show_all_cols = st.toggle("🔍 展開顯示所有詳細欄位", value=False)

        # 🌟 核心修正：直接使用已經被上方「營運數據看板」篩選好的 df_dash，取代原始的 df_orders
        df_display = df_dash.copy()
        
        if not df_display.empty:
            # 1. 執行狀態篩選
            if status_filter != "全部": 
                df_display = df_display[df_display['取貨狀態'] == status_filter]
                
            # 2. 執行關鍵字搜尋
            if search_kw.strip():
                mask = (
                    df_display['訂單編號'].astype(str).str.contains(search_kw, case=False, na=False) |
                    df_display['姓名'].astype(str).str.contains(search_kw, case=False, na=False) |
                    df_display['電話'].astype(str).str.contains(search_kw, case=False, na=False) |
                    df_display['信箱'].astype(str).str.contains(search_kw, case=False, na=False) |
                    df_display['物流編號'].astype(str).str.contains(search_kw, case=False, na=False)
                )
                df_display = df_display[mask]

        if not df_display.empty:
            select_all = st.checkbox(f"☑️ 全選下方所有顯示的 {len(df_display)} 筆訂單")
            df_display.insert(0, "🗑️ 勾選", select_all)
        
        # 定義高亮重複客的風格套用函數 (僅針對姓名、電話、信箱個別上色)
        def highlight_repeats(row):
            styles = [''] * len(row)
            for i, col in enumerate(row.index):
                val = row.get(col, '')
                # 若該格有值，且在重複次數統計中大於 1，則標記黃底黑字 (加上黑字確保暗黑模式也看得清楚)
                if col == '姓名' and val and name_counts.get(val, 0) > 1:
                    styles[i] = 'background-color: #ffcc00; color: #000000;'
                elif col == '電話' and val and phone_counts.get(val, 0) > 1:
                    styles[i] = 'background-color: #ffcc00; color: #000000;'
                elif col == '信箱' and val and email_counts.get(val, 0) > 1:
                    styles[i] = 'background-color: #ffcc00; color: #000000;'
            return styles

        col_cfg = {
            "🗑️ 勾選": st.column_config.CheckboxColumn("🗑️ 刪除", default=False),
            "⚠️ 警示": st.column_config.TextColumn("⚠️ 警示", disabled=True),
            # 👇 新增這行：設定為 DatetimeColumn，並指定顯示格式包含時分秒 👇
            "訂單日期": st.column_config.DatetimeColumn("訂單日期", format="YYYY-MM-DD HH:mm", disabled=True),
            # 👆 新增結束 👆
            "訂單編號": st.column_config.TextColumn("訂單編號", disabled=True),
            "訂單連結": st.column_config.LinkColumn("🔗 訂單連結"),
            "包裹應收": st.column_config.NumberColumn("包裹應收", format="$ %.0f"),
            "商品成本": st.column_config.NumberColumn("商品成本", format="$ %.0f"),
            "物流運費": st.column_config.NumberColumn("物流運費", format="$ %.0f"),
            "出貨成本": st.column_config.NumberColumn("出貨成本", format="$ %.0f", disabled=True),
            "訂單損益": st.column_config.NumberColumn("訂單損益", format="$ %.0f", disabled=True),
            "取貨狀態": st.column_config.SelectboxColumn("狀態", options=STATUS_LIST),
            "品項預覽": st.column_config.TextColumn("📦 品項內容 (預覽)", disabled=True),
            "信箱": st.column_config.TextColumn("📧 信箱"),
            "顧客備註": st.column_config.TextColumn("👤 顧客備註"),
            "商家備註": st.column_config.TextColumn("🏪 商家備註")
        }

        # 🚀 終極解決方案：不再與 Streamlit 的底層 CSS 渲染機制打架
        # 改用我們已經算好的 is_repeat，轉換成一個極度顯眼的專屬標籤欄位
        if not df_display.empty:
            df_display['⚠️ 警示'] = df_display['is_repeat'].apply(lambda x: '🚨 重複' if x else '')

        if show_all_cols:
            display_cols = ["🗑️ 勾選", "⚠️ 警示", "訂單日期", "訂單編號", "訂單連結", "姓名", "電話", "信箱", "門市", "店號", "品項預覽", "包裹應收", "商品成本", "物流運費", "出貨成本", "訂單損益", "物流編號", "取貨狀態", "取貨日期", "顧客備註", "商家備註"]
        else:
            # 預設把信箱、顧客備註、商家備註拿掉，讓它們「縮起來」
            display_cols = ["🗑️ 勾選", "⚠️ 警示", "訂單編號", "訂單日期", "姓名", "電話", "品項預覽", "包裹應收", "出貨成本", "訂單損益", "物流編號", "取貨狀態"]

        if not df_display.empty:
            # 1. 確保訂單日期是真正的 datetime 格式 (才能精準排序與格式化)
            df_display['訂單日期'] = pd.to_datetime(df_display['訂單日期'], errors='coerce')
            
            # 2. 依照訂單日期排序 (由新到舊，最新的在最上面)
            df_display = df_display.sort_values(by='訂單日期', ascending=False)
            
            # 3. 只保留要顯示的欄位
            df_display = df_display[display_cols]
        else:
            df_display = pd.DataFrame(columns=display_cols)
            
        # 動態將我們新增的警示欄位加入設定，並設為不可編輯
        col_cfg["⚠️ 警示"] = st.column_config.TextColumn("⚠️ 警示", disabled=True)

        # 直接放入乾淨的 DataFrame，徹底放棄會導致系統錯亂的 styled_df
        edited_orders = st.data_editor(
            df_display,
            disabled=not can_edit,
            hide_index=True,
            use_container_width=True,
            num_rows="fixed", 
            column_config=col_cfg,
            key="orders_editor"
        )

        if can_edit:
            # 🌟 將按鈕區塊改回 4 欄，移除「儲存上方總表狀態變更」按鈕
            c_export_label, c_export_detail, c_export_reship, c_del = st.columns(4)
            
            # 取得被勾選的訂單編號
            selected_orders = edited_orders[edited_orders["🗑️ 勾選"] == True]['訂單編號'].tolist() if not edited_orders.empty and "🗑️ 勾選" in edited_orders.columns else []

            # 🌟 原有功能：導出列印面單區塊
            with c_export_label:
                if len(selected_orders) > 0:
                    df_selected = df_orders[df_orders['訂單編號'].isin(selected_orders)].copy()
                    df_export = pd.DataFrame()
                    
                    df_export['订单号'] = df_selected['訂單編號']
                    df_export['运单号'] = '系統获取单号'
                    df_export['备注'] = df_selected['品項預覽']
                    df_export['货物类型'] = '商业件普货'
                    df_export['货物数量'] = '1'
                    df_export['品名'] = '香水'
                    df_export['目的地'] = '台湾'
                    df_export['时效'] = '空运'
                    df_export['承运商'] = df_selected['門市'].apply(lambda x: '銥熙-全家' if '全家' in str(x) else '銥熙7-11')
                    df_export['代收货款'] = df_selected['包裹應收']
                    df_export['包税(1包税2不包税)'] = ''
                    df_export['收件人地址'] = ''
                    df_export['收件人手机'] = df_selected['電話']
                    df_export['收件人姓名'] = df_selected['姓名']
                    df_export['申报数量'] = '1'
                    df_export['申报价值'] = '1'
                    df_export['申报单价'] = '10'
                    df_export['门店名称'] = df_selected['門市']
                    df_export['门店号码'] = df_selected['店號']
                    
                    import io
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_export.to_excel(writer, index=False, sheet_name='Sheet1')
                    
                    file_name = f"资料导入(代收付)_{pd.Timestamp.today().strftime('%Y%m%d_%H%M')}.xlsx"
                    
                    def mark_as_preparing():
                        try:
                            with get_db() as conn:
                                cursor = conn.cursor()
                                placeholders = ','.join(['?'] * len(selected_orders))
                                cursor.execute(f"UPDATE customer_orders SET 取貨狀態='備貨中' WHERE 訂單編號 IN ({placeholders})", tuple(selected_orders))
                                conn.commit()
                        except Exception as e:
                            pass

                    st.download_button(
                        label=f"📥 列印面單 ({len(selected_orders)} 筆)",
                        data=output.getvalue(),
                        file_name=file_name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary",
                        use_container_width=True,
                        on_click=mark_as_preparing
                    )
                else:
                    st.button("📥 請先勾選", disabled=True, use_container_width=True, key="btn_no_label")

            # 🌟 原有功能：導出完整詳細資料區塊
            with c_export_detail:
                if len(selected_orders) > 0:
                    import io
                    df_selected_detail = df_orders[df_orders['訂單編號'].isin(selected_orders)].copy()
                    
                    # 👇 新增這行：將匯出表單內的編碼替換為翻譯後的中文明細
                    df_selected_detail['品項內容'] = df_selected_detail['品項翻譯']
                    
                    # 👇 修改這行：要把 '品項翻譯' 也加入忽略清單，不要匯出多餘的欄位
                    cols_to_drop = ['is_repeat', '品項內容_原始', '品項預覽', '品項翻譯', '下單總數', '物流運費_RMB']
                    df_selected_detail = df_selected_detail.drop(columns=[c for c in cols_to_drop if c in df_selected_detail.columns])

                    output_detail = io.BytesIO()
                    with pd.ExcelWriter(output_detail, engine='openpyxl') as writer:
                        df_selected_detail.to_excel(writer, index=False, sheet_name='訂單詳細資料')
                    
                    file_name_detail = f"訂單詳細匯出_{pd.Timestamp.today().strftime('%Y%m%d_%H%M')}.xlsx"

                    st.download_button(
                        label=f"📊 詳細資料 ({len(selected_orders)} 筆)",
                        data=output_detail.getvalue(),
                        file_name=file_name_detail,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.button("📊 請先勾選", disabled=True, use_container_width=True, key="btn_no_detail")

            # 🌟 全新功能：深港台重出表格導出
            with c_export_reship:
                if len(selected_orders) > 0:
                    import io
                    df_selected_reship = df_orders[df_orders['訂單編號'].isin(selected_orders)].copy()
                    df_reship = pd.DataFrame()
                    
                    df_reship['主號'] = ""
                    df_reship['袋號'] = ""
                    df_reship['原單號'] = ""
                    df_reship['運單重量'] = ""
                    df_reship['收件人電話'] = df_selected_reship['電話']
                    df_reship['收件人姓名'] = df_selected_reship['姓名']
                    df_reship['超商代碼'] = df_selected_reship['店號']
                    df_reship['超商名稱'] = df_selected_reship['門市']
                    df_reship['超商地址'] = ""
                    df_reship['代收貨款'] = df_selected_reship['包裹應收']
                    df_reship['貨物價值'] = ""
                    df_reship['品名'] = '香水'
                    df_reship['寄件人公司'] = '深港台'
                    df_reship['寄件人姓名'] = '深港台'
                    df_reship['寄件人電話'] = '03-4498990'
                    df_reship['寄件人地址'] = '桃園市中壢區內定八街790號'

                    output_reship = io.BytesIO()
                    with pd.ExcelWriter(output_reship, engine='openpyxl') as writer:
                        df_reship.to_excel(writer, index=False, sheet_name='Sheet1')
                    
                    # 檔名自動生成，例如：深港台重出0714.xlsx
                    file_name_reship = f"深港台重出{pd.Timestamp.today().strftime('%m%d')}.xlsx"

                    st.download_button(
                        label=f"📦 重出單 ({len(selected_orders)} 筆)",
                        data=output_reship.getvalue(),
                        file_name=file_name_reship,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.button("📦 請先勾選", disabled=True, use_container_width=True, key="btn_no_reship")

            # 🌟 原有功能：刪除訂單區塊
            with c_del:
                if len(selected_orders) > 0:
                    if st.button(f"⚠️ 刪除 ({len(selected_orders)} 筆)", type="primary", use_container_width=True):
                        try:
                            with get_db() as conn:
                                cursor = conn.cursor()
                                placeholders = ','.join(['?'] * len(selected_orders))
                                cursor.execute(f"DELETE FROM customer_orders WHERE 訂單編號 IN ({placeholders})", tuple(selected_orders))
                                conn.commit()
                            log_system_action("訂單明細", current_operator, "刪除訂單資料", f"刪除了 {len(selected_orders)} 筆訂單")
                            st.success(f"✅ 成功刪除 {len(selected_orders)} 筆訂單！")
                            time.sleep(1); st.rerun()
                        except Exception as e:
                            st.error(f"❌ 刪除失敗：{str(e)}")
                else:
                    st.button("⚠️ 請先勾選", disabled=True, use_container_width=True, key="btn_no_del")

        st.divider()

        # 👇 單筆訂單完整詳細檢視與獨立編輯區 👇
        st.subheader("🔍 單筆訂單完整詳細檢視與編輯")
        if not df_orders.empty:
            detail_options = {}
            for _, row in df_orders.iterrows():
                logi_info = row.get('物流編號', '').strip()
                logi_str = f" ｜ 物流: {logi_info}" if logi_info else ""
                label = f"[{row['訂單編號']}] {row.get('姓名', '')}{logi_str}"
                detail_options[label] = row['訂單編號']
            
            selected_label = st.selectbox("💡 支援直接點擊此處，用鍵盤打字搜尋「物流單號」、「姓名」或「訂單編號」：", options=list(detail_options.keys()))
            selected_order = detail_options.get(selected_label)
            
            if selected_order:
                target_order = df_orders[df_orders['訂單編號'] == selected_order].iloc[0]
                
                with st.form(f"detail_edit_form_{selected_order}"):
                    st.markdown(f"### 🧾 訂單編號：`{selected_order}`")
                    
                    # 🚀 新增：智能顯示重複客詳細資訊 (包含歷史訂單狀態)
                    if target_order.get('is_repeat', False):
                        dup_msgs = []
                        
                        if target_order['姓名'] and name_counts.get(target_order['姓名'], 0) > 1:
                            dup_df = df_orders[(df_orders['姓名'] == target_order['姓名']) & (df_orders['訂單編號'] != selected_order)]
                            dup_info = [f"{row['訂單編號']} ({row.get('取貨狀態', '未知')})" for _, row in dup_df.iterrows()]
                            dup_msgs.append(f"👤 姓名【{target_order['姓名']}】👉 歷史單號：{', '.join(dup_info)}")
                            
                        if target_order['電話'] and phone_counts.get(target_order['電話'], 0) > 1:
                            dup_df = df_orders[(df_orders['電話'] == target_order['電話']) & (df_orders['訂單編號'] != selected_order)]
                            dup_info = [f"{row['訂單編號']} ({row.get('取貨狀態', '未知')})" for _, row in dup_df.iterrows()]
                            dup_msgs.append(f"📞 電話【{target_order['電話']}】👉 歷史單號：{', '.join(dup_info)}")
                            
                        if target_order['信箱'] and email_counts.get(target_order['信箱'], 0) > 1:
                            dup_df = df_orders[(df_orders['信箱'] == target_order['信箱']) & (df_orders['訂單編號'] != selected_order)]
                            dup_info = [f"{row['訂單編號']} ({row.get('取貨狀態', '未知')})" for _, row in dup_df.iterrows()]
                            dup_msgs.append(f"📧 信箱【{target_order['信箱']}】👉 歷史單號：{', '.join(dup_info)}")
                        
                        if dup_msgs:
                            st.error("🚨 **系統偵測此為重複客，歷史紀錄與狀態對比：**\n\n" + "\n\n".join(dup_msgs))
                    
                    c1, c2, c3, c4, c5 = st.columns(5)
                    edit_date = c1.text_input("訂單日期", value=target_order.get('訂單日期', ''))
                    edit_name = c2.text_input("顧客姓名", value=target_order.get('姓名', ''))
                    edit_phone = c3.text_input("聯絡電話", value=target_order.get('電話', ''))
                    edit_email = c4.text_input("📧 聯絡信箱", value=target_order.get('信箱', ''))
                    edit_link = c5.text_input("訂單連結", value=target_order.get('訂單連結', ''))

                    # 🌟 將 4 欄改成 5 欄，新增取貨日期編輯框
                    c6, c7, c8, c9, c9a = st.columns(5)
                    edit_store = c6.text_input("取件門市", value=target_order.get('門市', ''))
                    edit_store_id = c7.text_input("門市店號", value=target_order.get('店號', ''))
                    edit_logistics = c8.text_input("物流編號", value=target_order.get('物流編號', ''))
                    
                    status_opts = STATUS_LIST.copy()
                    current_status = target_order.get('取貨狀態', '待出貨')
                    if current_status not in status_opts: status_opts.append(current_status)
                    edit_status = c9.selectbox("取貨狀態", options=status_opts, index=status_opts.index(current_status))
                    
                    # 🌟 將取貨日期改為「日期選擇器 (日曆)」，並安全解析舊資料
                    raw_pickup = target_order.get('取貨日期', None)
                    parsed_date = None
                    if pd.notna(raw_pickup) and str(raw_pickup).strip() not in ['', 'nan', 'None']:
                        try:
                            parsed_date = pd.to_datetime(raw_pickup).date()
                        except:
                            parsed_date = None
                    
                    edit_pickup = c9a.date_input("取貨日期", value=parsed_date, format="YYYY/MM/DD")

                    st.markdown("##### 💰 金額與成本核算 (應收與成本為台幣，運費請輸入人民幣)")
                    c10, c11, c12 = st.columns(3)
                    edit_revenue = c10.number_input("包裹應收 (TWD)", value=float(target_order.get('包裹應收', 0.0)), step=10.0)
                    edit_cost = c11.number_input("商品成本 (TWD)", value=float(target_order.get('商品成本', 0.0)), step=10.0)
                    
                    # 🌟 雙重防呆：確保讀取到的 RMB 運費有效，若是空值或 NaN 則預設為 0.0
                    raw_rmb = target_order.get('物流運費_RMB', 0.0)
                    current_shipping_rmb = float(raw_rmb) if pd.notna(raw_rmb) else 0.0
                    
                    edit_shipping_rmb = c12.number_input("物流運費 (RMB)", value=current_shipping_rmb, step=1.0)
                    edit_shipping = edit_shipping_rmb * rate  # 換算為台幣供後續運算
                    
                    c12.caption(f"🔄 預估台幣運費：**{edit_shipping:,.0f}** TWD (依匯率 {rate})")

                    db_ship_cost = float(target_order.get('出貨成本', 0.0))
                    db_profit = float(target_order.get('訂單損益', 0.0))
                    st.caption(f"📝 目前存檔狀態 👉 系統結算之出貨總成本：**{db_ship_cost:,.0f}** ｜ 訂單最終損益：**{db_profit:,.0f}**")

                    # 👇 更改提示字眼
                    new_items = st.text_area("📦 品項內容 (支援直接換行編輯，請保持原始編碼以利系統精準追蹤)", value=target_order.get('品項內容_原始', ''), height=150)
                    
                    # 👇 修正這裡：使用 replace 把 * 加上跳脫字元 \\*，防止被系統誤認成斜體語法
                    safe_preview = target_order.get('品項翻譯', '無品項').replace('*', '\\*')
                    st.info(f"👁️ **系統自動翻譯對照**：\n\n{safe_preview}")
                    
                    c14, c15 = st.columns(2)
                    edit_cust_note = c14.text_area("👤 顧客備註", value=target_order.get('顧客備註', ''))
                    edit_merch_note = c15.text_area("🏪 商家備註", value=target_order.get('商家備註', ''))

                    if can_edit:
                        if st.form_submit_button("💾 儲存這筆訂單的所有完整變更", type="primary", use_container_width=True):
                            try:
                                calc_single_ship_cost = edit_cost + edit_shipping
                                calc_single_profit = edit_revenue - calc_single_ship_cost
                                
                                # 🌟 這裡是最關鍵的防呆：純日期物件轉換，絕對不能有 .strip()
                                sql_pickup = edit_pickup.strftime('%Y-%m-%d') if edit_pickup else None
                                
                                with get_db() as conn:
                                    # 🌟 寫入資料庫時加上 取貨日期
                                    conn.execute("""
                                        UPDATE customer_orders SET 
                                        訂單日期=?, 姓名=?, 電話=?, 信箱=?, 訂單連結=?, 
                                        門市=?, 店號=?, 物流編號=?, 取貨狀態=?, 取貨日期=?,
                                        包裹應收=?, 商品成本=?, 物流運費=?, 物流運費_RMB=?, 出貨成本=?, 訂單損益=?,
                                        品項內容=?, 顧客備註=?, 商家備註=?
                                        WHERE 訂單編號=?
                                    """, (
                                        edit_date, edit_name, edit_phone, edit_email, edit_link,
                                        edit_store, edit_store_id, edit_logistics, edit_status, sql_pickup,
                                        edit_revenue, edit_cost, edit_shipping, edit_shipping_rmb, calc_single_ship_cost, calc_single_profit,
                                        new_items, edit_cust_note, edit_merch_note, selected_order
                                    ))
                                    conn.commit()
                                log_system_action("訂單明細", current_operator, "編輯單筆完整訂單", f"全面更新了訂單 {selected_order} 的詳細資訊與備註")
                                st.success(f"✅ 訂單 {selected_order} 資訊更新成功！出貨成本結算為 {calc_single_ship_cost:,.0f}，損益為 {calc_single_profit:,.0f}。")
                                time.sleep(1.5); st.rerun()
                            except Exception as e:
                                st.error(f"❌ 更新失敗：{str(e)}")
                    else:
                        st.form_submit_button("🔒 您無權限編輯這筆訂單", disabled=True)

                # 🌟 新增功能：已上架訂單的重出作業 (獨立於上方的編輯表單外)
                if target_order.get('取貨狀態') == '已上架' and can_edit:
                    st.markdown("---")
                    st.markdown("#### 🔄 庫存轉單重出作業")
                    st.info("💡 此功能可將目前這筆「已上架」的包裹，直接轉配給另一位「待出貨 / 備貨中」的客人。系統將自動為雙方加上備註，並幫新訂單計算重出的運費成本。")
                    
                    # 尋找可以接收此包裹的訂單 (待出貨或備貨中)
                    pending_orders = df_orders[df_orders['取貨狀態'].isin(['待出貨', '備貨中'])]
                    if pending_orders.empty:
                        st.warning("目前系統中沒有「待出貨」或「備貨中」的訂單可供轉配。")
                    else:
                        # 準備選單字典，避免同名覆蓋
                        pending_opts = {}
                        for _, prow in pending_orders.iterrows():
                            plabel = f"[{prow['訂單編號']}] {prow.get('姓名','')} (應收: ${float(prow.get('包裹應收',0)):,.0f})"
                            pending_opts[plabel] = prow['訂單編號']
                        
                        c_transfer1, c_transfer2 = st.columns([2, 1])
                        with c_transfer1:
                            target_pending_label = st.selectbox("🎯 選擇接收此包裹的新訂單：", options=list(pending_opts.keys()))
                            target_pending_oid = pending_opts[target_pending_label]
                        with c_transfer2:
                            reship_fee_rmb = st.number_input("💸 本次重出的新運費 (RMB)", value=0.0, step=1.0)
                            reship_fee_twd = reship_fee_rmb * rate
                            st.caption(f"預估台幣：**{reship_fee_twd:,.0f}** TWD")
                            
                        if st.button("🚀 確認執行轉單重出", type="primary", use_container_width=True):
                            try:
                                with get_db() as conn:
                                    cursor = conn.cursor()
                                    
                                    # 1. 更新原訂單 (改為已重出，加上追蹤備註)
                                    orig_merch_note = target_order.get('商家備註', '')
                                    new_orig_note = f"{orig_merch_note}\n[系統] 於 {pd.Timestamp.today().strftime('%Y-%m-%d')} 轉單重出給 {target_pending_oid}".strip()
                                    cursor.execute("UPDATE customer_orders SET 取貨狀態='已重出', 商家備註=? WHERE 訂單編號=?", (new_orig_note, selected_order))
                                    
                                    # 2. 獲取原包裹 (已上架) 的實際品項與商品成本 (準備轉移)
                                    orig_items = str(target_order.get('品項內容_原始', target_order.get('品項內容', ''))).strip()
                                    orig_cost = float(target_order.get('商品成本', 0.0))
                                    
                                    # 3. 獲取目標接收訂單的現有資訊 (保留它自己的包裹應收，因為這是新客人的成交價)
                                    target_row = pending_orders[pending_orders['訂單編號'] == target_pending_oid].iloc[0]
                                    t_old_items = str(target_row.get('品項內容_原始', target_row.get('品項內容', ''))).strip()
                                    t_merch_note = target_row.get('商家備註', '')
                                    t_rev = float(target_row.get('包裹應收', 0.0))  # 保持新訂單原有的應收金額
                                    
                                    # 重新結算新訂單出貨成本 (原包裹商品成本 + 本次重出的新運費)
                                    calc_t_ship_cost = orig_cost + reship_fee_twd
                                    # 重新結算訂單損益 (新訂單的應收金額 - 剛算出的出貨成本)
                                    calc_t_profit = t_rev - calc_t_ship_cost
                                    
                                    # 將新訂單原本點的商品，記錄到商家備註中備查
                                    new_t_note = f"{t_merch_note}\n[系統] 接收物流上架包裹 {selected_order}，並支付重出運費 RMB {reship_fee_rmb}。\n[系統] 客戶原訂商品保留紀錄：{t_old_items}".strip()
                                    
                                    # 更新資料庫：寫入新品項、新成本、新運費，並推進狀態 (包裹應收保持不變)
                                    cursor.execute("""
                                        UPDATE customer_orders 
                                        SET 品項內容=?, 商品成本=?, 物流運費_RMB=?, 物流運費=?, 出貨成本=?, 訂單損益=?, 取貨狀態='備貨中', 商家備註=?
                                        WHERE 訂單編號=?
                                    """, (orig_items, orig_cost, reship_fee_rmb, reship_fee_twd, calc_t_ship_cost, calc_t_profit, new_t_note, target_pending_oid))
                                    
                                    conn.commit()
                                    
                                log_system_action("訂單明細", current_operator, "轉單重出", f"將已上架訂單 {selected_order} 重出給 {target_pending_oid}")
                                st.success(f"✅ 成功將包裹轉配給 {target_pending_oid}！原訂單已標記為「已重出」。")
                                time.sleep(1.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 轉單失敗：{str(e)}")

    with t2:
        st.subheader("✍️ 手動新增單筆訂單")
        if not can_edit:
            st.warning("🔒 您沒有新增訂單的權限。")
        else:
            with st.form("manual_add_order_form"):
                c_ma1, c_ma2, c_ma3 = st.columns(3)
                ma_oid = c_ma1.text_input("訂單編號 (必填)*")
                ma_date = c_ma2.text_input("訂單日期 (如: 2026-07-08)", value=pd.Timestamp.today().strftime('%Y-%m-%d'))
                ma_name = c_ma3.text_input("顧客姓名")
                
                c_ma4, c_ma5, c_ma6 = st.columns(3)
                ma_phone = c_ma4.text_input("聯絡電話")
                ma_email = c_ma5.text_input("聯絡信箱")
                ma_link = c_ma6.text_input("訂單連結")
                
                c_ma7, c_ma8, c_ma9 = st.columns(3)
                ma_store = c_ma7.text_input("取件門市 (承運商)")
                ma_store_id = c_ma8.text_input("門市店號")
                ma_status = c_ma9.selectbox("初始狀態", options=STATUS_LIST, index=0)
                
                c_ma10, c_ma11, c_ma12 = st.columns(3)
                ma_revenue = c_ma10.number_input("包裹應收 (TWD)", value=0.0, step=10.0)
                ma_cost = c_ma11.number_input("商品成本 (TWD)", value=0.0, step=10.0)
                
                # 🌟 新增時運費改為輸入 RMB 並自動換算台幣存檔
                ma_shipping_rmb = c_ma12.number_input("物流運費 (RMB)", value=0.0, step=1.0)
                ma_shipping = ma_shipping_rmb * rate  # 儲存時自動轉回台幣
                c_ma12.caption(f"🔄 預估台幣運費：**{ma_shipping:,.0f}** TWD (依匯率 {rate})")
                
                ma_items = st.text_area("📦 品項內容 (支援多行備註)")
                
                c_ma13, c_ma14 = st.columns(2)
                ma_c_note = c_ma13.text_area("👤 顧客備註")
                ma_m_note = c_ma14.text_area("🏪 商家備註")
                
                if st.form_submit_button("🚀 儲存並新增這筆訂單", type="primary", use_container_width=True):
                    if not ma_oid.strip():
                        st.error("❌ 『訂單編號』不可為空！")
                    else:
                        try:
                            ma_ship_cost = ma_cost + ma_shipping
                            ma_profit = ma_revenue - ma_ship_cost
                            with get_db() as conn:
                                # 🌟 將 ma_shipping_rmb 一併寫入資料庫
                                conn.execute("""
                                    INSERT INTO customer_orders 
                                    (訂單編號, 訂單日期, 姓名, 電話, 信箱, 訂單連結, 門市, 店號, 品項內容, 包裹應收, 商品成本, 物流運費, 物流運費_RMB, 出貨成本, 訂單損益, 物流編號, 取貨狀態, 顧客備註, 商家備註, 下單總數)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, 0)
                                """, (
                                    ma_oid.strip(), ma_date, ma_name, ma_phone, ma_email, ma_link, ma_store, ma_store_id,
                                    ma_items, ma_revenue, ma_cost, ma_shipping, ma_shipping_rmb, ma_ship_cost, ma_profit, ma_status, ma_c_note, ma_m_note
                                ))
                                conn.commit()
                            log_system_action("訂單明細", current_operator, "手動新增訂單", f"新增了單筆訂單 {ma_oid}")
                            st.success(f"✅ 訂單 {ma_oid} 新增成功！")
                            time.sleep(1); st.rerun()
                        except Exception as e:
                            if "UNIQUE constraint failed" in str(e):
                                st.error("❌ 此訂單編號已存在資料庫中！請確認是否重複。")
                            else:
                                st.error(f"❌ 新增失敗：{str(e)}")

    with t3:
        st.subheader("📥 批量導入與更新工具")
        if not check_perm(role, "訂單明細", "can_upload"):
            st.warning("🔒 您沒有上傳外部訂單的權限。")
        else:
            exp1 = st.expander("📝 1. 批量導入【新訂單建立】 (將新訂單資料寫入系統)", expanded=True)
            with exp1:
                st.caption("💡 系統會自動過濾外部欄位並合併複數品項。若包含『信箱』、『顧客備註』、『商家備註』系統也會一併抓取匯入。")
                uploaded_order = st.file_uploader("選擇訂單檔案", type=["csv", "xlsx"], key="order_uploader")
                
                if uploaded_order and st.button("🚀 執行【建立新訂單】匯入", type="primary", key="btn_imp_orders"):
                    try:
                        df_imp = pd.read_csv(uploaded_order) if uploaded_order.name.endswith('.csv') else pd.read_excel(uploaded_order, engine='openpyxl')
                        
                        col_mapping = {
                            '訂單編號': '訂單編號', '建立日期': '訂單日期', '收件人': '姓名', '貨號': '品項內容',
                            '總計金額': '包裹應收', '聯絡電話': '電話', '連絡電話': '電話', 'Email': '信箱', '信箱': '信箱', 
                            '運送超商': '門市', '超商代號': '店號',
                            '顧客備註': '顧客備註', '商家備註': '商家備註',
                            '超商寄貨編號(拋單後取得)': '物流編號', '物流編號': '物流編號'
                        }
                        df_imp = df_imp.rename(columns=col_mapping)

                        # 👇 新增這段：在資料被 fillna 和 groupby 破壞前，強制鎖定格式 (年-月-日 時:分) 👇
                        if '訂單日期' in df_imp.columns:
                            df_imp['訂單日期'] = pd.to_datetime(df_imp['訂單日期'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M')
                        # 👆 新增結束 👆
                        
                        if '訂單編號' not in df_imp.columns:
                            st.error("❌ 匯入失敗：檔案中找不到『訂單編號』欄位。")
                        else:
                            df_imp = df_imp[df_imp['訂單編號'].astype(str).str.strip() != ""]
                            
                            if '包裹應收' in df_imp.columns:
                                if df_imp['包裹應收'].dtype == object: df_imp['包裹應收'] = df_imp['包裹應收'].astype(str).str.replace(',', '')
                                df_imp['包裹應收'] = pd.to_numeric(df_imp['包裹應收'], errors='coerce').fillna(0.0)
                                
                            df_imp = df_imp.fillna("")
                            agg_funcs = {}
                            for col in df_imp.columns:
                                if col == '訂單編號': continue
                                elif col == '品項內容': agg_funcs[col] = lambda x: '\n'.join([f"• {str(i).strip()}" for i in x if str(i).strip() != ""])
                                else: agg_funcs[col] = 'first' 
                                    
                            df_grouped = df_imp.groupby('訂單編號', as_index=False).agg(agg_funcs)

                            # 🌟 1. 取得總筆數，並初始化新訂單匯入的進度條
                            total_rows = len(df_grouped)
                            progress_bar = st.progress(0, text=f"準備匯入 {total_rows} 筆訂單...")

                            with get_db() as conn:
                                cursor = conn.cursor()
                                count = 0
                                # 🌟 2. 加入 enumerate 來追蹤目前的迴圈次數 (i)
                                for i, (_, row) in enumerate(df_grouped.iterrows()):
                                    rev = float(row.get('包裹應收', 0.0))
                                    
                                    raw_order_status = str(row.get('訂單狀態', row.get('订单状态', ''))).strip()
                                    if raw_order_status in ['已取消', '其他']:
                                        init_status = '已取消'
                                    else:
                                        init_status = '待出貨'

                                    # 修正日期時間抓取：使用 Pandas 內建功能確保時間格式被完整保留
                                    raw_date = row.get('訂單日期')
                                    if pd.isna(raw_date) or str(raw_date).strip() == '':
                                        order_date = None
                                    else:
                                        # 嘗試將任何格式轉回標準的 YYYY-MM-DD HH:MM:SS 字串
                                        try:
                                            order_date = pd.to_datetime(raw_date).strftime('%Y-%m-%d %H:%M:%S')
                                        except:
                                            # 如果轉換失敗，就保留原始文字
                                            order_date = str(raw_date).strip()
                                    
                                    store_name = str(row.get('門市', '')).strip()
                                    raw_logi = str(row.get('物流編號', '')).strip()
                                    
                                    if raw_logi and raw_logi.lower() not in ['nan', 'none']:
                                        if raw_logi.endswith('.0'): raw_logi = raw_logi[:-2] 
                                        if '全家' in store_name and not raw_logi.startswith('0'):
                                            raw_logi = '0' + raw_logi
                                    else:
                                        raw_logi = ''

                                    cursor.execute("""
                                        INSERT INTO customer_orders 
                                        (訂單編號, 訂單日期, 姓名, 電話, 信箱, 門市, 店號, 品項內容, 下單總數, 包裹應收, 商品成本, 物流運費, 出貨成本, 訂單損益, 物流編號, 取貨狀態, 取貨日期, 顧客備註, 商家備註)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 0.0, 0.0, 0.0, ?, ?, ?, NULL, ?, ?)
                                        ON CONFLICT(訂單編號) DO UPDATE SET
                                            訂單日期 = excluded.訂單日期,
                                            姓名 = excluded.姓名,
                                            電話 = excluded.電話,
                                            信箱 = excluded.信箱,
                                            門市 = excluded.門市,
                                            店號 = excluded.店號,
                                            品項內容 = excluded.品項內容,
                                            包裹應收 = excluded.包裹應收,
                                            訂單損益 = excluded.包裹應收 - customer_orders.出貨成本,
                                            物流編號 = CASE WHEN excluded.物流編號 != '' THEN excluded.物流編號 ELSE customer_orders.物流編號 END,
                                            取貨狀態 = CASE WHEN excluded.取貨狀態 = '已取消' THEN '已取消' ELSE customer_orders.取貨狀態 END,
                                            顧客備註 = excluded.顧客備註,
                                            商家備註 = excluded.商家備註;
                                    """, (
                                        str(row['訂單編號']).strip(), 
                                        order_date,
                                        str(row.get('姓名', '')),
                                        str(row.get('電話', '')), 
                                        str(row.get('信箱', '')), 
                                        store_name, 
                                        str(row.get('店號', '')),
                                        str(row.get('品項內容', '')), 
                                        rev, 
                                        rev, 
                                        raw_logi, 
                                        init_status,
                                        str(row.get('顧客備註', '')), 
                                        str(row.get('商家備註', ''))
                                    ))
                                    count += 1
                                    
                                    # 🌟 3. 每次迴圈結束更新進度條與文字
                                    progress_bar.progress((i + 1) / total_rows, text=f"匯入進度：{i + 1} / {total_rows} 筆 (成功寫入: {count} 筆)")
                                    
                                conn.commit()
                                
                            log_system_action("訂單明細", current_operator, "匯入訂單資料", f"成功批次合併與匯入了 {count} 筆訂單，並更新了物流單號")
                            st.success(f"✅ 成功匯入並智能合併為 {count} 筆獨立訂單！")
                            time.sleep(1.5); st.rerun()
                    except Exception as e:
                        st.error(f"❌ 匯入失敗，詳情：{str(e)}")
            
            exp2 = st.expander("🚚 2. 批量導入【更新物流單號、狀態與運費】", expanded=False)
            with exp2:
                st.caption("💡 系統會以表格內的『訂單編號/订单号』尋找系統中對應的單號，並替換該單的【狀態】、【物流單號/运单号】、【運費/运费】。並重新幫您核算單筆利潤。")
                
                st.info(f"💱 系統將自動套用側邊欄目前的匯率：**{rate}**。若物流單內填寫的是人民幣，系統會自動轉換為台幣存檔。")
                uploaded_logi = st.file_uploader("選擇物流更新檔案", type=["csv", "xlsx"], key="logi_uploader")
                
                exchange_rate = rate
                
                if uploaded_logi and st.button("🚀 執行【物流資訊】比對更新", type="primary", key="btn_update_logi"):
                        try:
                            df_logi = pd.read_csv(uploaded_logi) if uploaded_logi.name.endswith('.csv') else pd.read_excel(uploaded_logi, engine='openpyxl')
                            
                            l_map = {
                                '订单号': '訂單編號', '订单编号': '訂單編號', '訂單號': '訂單編號', '订单号码': '訂單編號',
                                '状态': '狀態', '订单状态': '狀態', '取貨狀態': '狀態',
                                '承运单号': '物流編號', '交货单号': '物流編號',  '物流單號': '物流編號',
                                '运费': '物流運費', '实际运费': '物流運費',
                                '末条时间': '取貨日期', '取货时间': '取貨日期'
                            }
                            df_logi = df_logi.rename(columns=l_map)
                            
                            if '訂單編號' not in df_logi.columns:
                                st.error("❌ 檔案中找不到基準欄位『訂單編號』(或订单号码)，無法比對。")
                            else:
                                df_logi = df_logi[df_logi['訂單編號'].astype(str).str.strip() != ""]
                                
                                has_status = '狀態' in df_logi.columns
                                has_logi_num = '物流編號' in df_logi.columns
                                has_fee = '物流運費' in df_logi.columns
                                has_date = '取貨日期' in df_logi.columns
                                
                                if not (has_status or has_logi_num or has_fee or has_date):
                                    st.error("❌ 檔案中必須包含『狀態』、『发货单号』、『運費』或『末条时间』至少其中一欄。")
                                else:
                                    if has_fee:
                                        if df_logi['物流運費'].dtype == object: df_logi['物流運費'] = df_logi['物流運費'].astype(str).str.replace(',', '')
                                        df_logi['物流運費'] = pd.to_numeric(df_logi['物流運費'], errors='coerce').fillna(0.0)
                                        
                                    df_logi = df_logi.fillna("")
                                    update_count = 0
                                    
                                    # 🌟 4. 取得總筆數，並初始化物流更新的進度條
                                    total_logi_rows = len(df_logi)
                                    progress_bar_logi = st.progress(0, text=f"準備比對更新 {total_logi_rows} 筆物流資料...")
                                    
                                    with get_db() as conn:
                                        cursor = conn.cursor()
                                        # 🌟 5. 加入 enumerate 來追蹤目前的迴圈次數 (i)
                                        for i, (_, row) in enumerate(df_logi.iterrows()):
                                            oid = str(row['訂單編號']).strip()
                                            
                                            cursor.execute("SELECT 包裹應收, 商品成本, 物流運費, 物流運費_RMB FROM customer_orders WHERE 訂單編號=?", (oid,))
                                            db_row = cursor.fetchone()
                                            
                                            if db_row:
                                                db_revenue, db_cost, db_shipping, db_shipping_rmb = db_row
                                                
                                                raw_status = str(row['狀態']).strip() if has_status and str(row['狀態']).strip() != "" else None
                                                
                                                status_map = {
                                                    '在途': '配送中', '待取件': '已送達待取', '签收': '簽收',
                                                    '退回': '退回', '退货上架': '已上架', '客诉': '客訴', '已重出': '已重出'
                                                }
                                                
                                                new_status = None
                                                if raw_status in status_map:
                                                    new_status = status_map[raw_status]
                                                elif raw_status in STATUS_LIST:
                                                    new_status = raw_status
                                                    
                                                new_logi_num = str(row['物流編號']).strip() if has_logi_num and str(row['物流編號']).strip() != "" else None
                                                
                                                if has_fee and str(row['物流運費']).strip() != "":
                                                    new_fee_rmb = float(row['物流運費'])
                                                    new_fee_twd = new_fee_rmb * exchange_rate
                                                else:
                                                    new_fee_rmb = float(db_shipping_rmb if db_shipping_rmb is not None else 0.0)
                                                    new_fee_twd = float(db_shipping)
                                                    
                                                if new_logi_num and not new_status:
                                                    new_status = '配送中'

                                                new_date = None
                                                if new_status == '簽收' and has_date and str(row['取貨日期']).strip() != "":
                                                    new_date = str(row['取貨日期']).strip()
                                                    
                                                calc_ship = float(db_cost) + new_fee_twd
                                                calc_profit = float(db_revenue) - calc_ship
                                                
                                                updates, params = [], []
                                                if new_status: updates.append("取貨狀態=?"); params.append(new_status)
                                                if new_logi_num: updates.append("物流編號=?"); params.append(new_logi_num)
                                                if new_date: updates.append("取貨日期=?"); params.append(new_date)
                                                
                                                updates.append("物流運費=?"); params.append(new_fee_twd)
                                                updates.append("物流運費_RMB=?"); params.append(new_fee_rmb)
                                                updates.append("出貨成本=?"); params.append(calc_ship)
                                                updates.append("訂單損益=?"); params.append(calc_profit)
                                                
                                                params.append(oid)
                                                
                                                if updates:
                                                    cursor.execute(f"UPDATE customer_orders SET {', '.join(updates)} WHERE 訂單編號=?", tuple(params))
                                                    update_count += 1
                                            
                                            # 🌟 6. 每次迴圈結束更新進度條與文字
                                            progress_bar_logi.progress((i + 1) / total_logi_rows, text=f"更新進度：{i + 1} / {total_logi_rows} 筆 (成功比對: {update_count} 筆)")
                                            
                                        conn.commit()
                                        
                                    log_system_action("訂單明細", current_operator, "批量更新物流", f"比對更新了 {update_count} 筆訂單資訊，匯率設定：{exchange_rate}")
                                    st.success(f"✅ 成功為 {update_count} 筆訂單掛載了最新物流與狀態資訊！(已依匯率 {exchange_rate} 轉換為台幣)")
                                    time.sleep(1.5); st.rerun()
                        except Exception as e:
                            st.error(f"❌ 更新失敗，詳情：{str(e)}")
                            
            # =========== 以下為新增的 exp3：依物流單號(承运单号)對應更新 ===========
            exp3 = st.expander("💰 3. 批量導入【依物流單號更新運費與狀態】", expanded=False)
            with exp3:
                st.caption("💡 系統會以表格內的『承运单号』尋找系統中對應的『物流編號』，並替換該單的【狀態】(状态) 與【運費】(运费)，若狀態為簽收則同步更新【取貨時間】(末条时间)，同時重新核算單筆利潤。")
                st.info(f"💱 系統將自動套用側邊欄目前的匯率：**{rate}**。若運費欄填寫的是人民幣，系統會自動轉換為台幣存檔。")
                
                uploaded_track = st.file_uploader("選擇依物流單號更新之檔案", type=["csv", "xlsx"], key="track_uploader")
                
                if uploaded_track and st.button("🚀 執行【依物流單號】比對更新", type="primary", key="btn_update_by_track"):
                    try:
                        df_track = pd.read_csv(uploaded_track) if uploaded_track.name.endswith('.csv') else pd.read_excel(uploaded_track, engine='openpyxl')
                        
                        # 🌟 新增：將「末条时间」、「取货时间」加入映射字典
                        t_map = {
                            '承运单号': '物流編號', '承運單號': '物流編號', '物流單號': '物流編號', '物流单号': '物流編號',
                            '状态': '狀態', '狀態': '狀態', '订单状态': '狀態', '取貨狀態': '狀態',
                            '运费': '物流運費', '運費': '物流運費', '实际运费': '物流運費',
                            '末条时间': '取貨日期', '末條時間': '取貨日期', '取货时间': '取貨日期', '取貨時間': '取貨日期'
                        }
                        df_track = df_track.rename(columns=t_map)
                        
                        if '物流編號' not in df_track.columns:
                            st.error("❌ 檔案中找不到基準欄位『承运单号』(或物流編號)，無法比對。")
                        else:
                            # 過濾掉空值的物流編號
                            df_track = df_track[df_track['物流編號'].astype(str).str.strip() != ""]
                            
                            has_status = '狀態' in df_track.columns
                            has_fee = '物流運費' in df_track.columns
                            has_date = '取貨日期' in df_track.columns  # 🌟 新增：偵測是否有時間欄位
                            
                            if not (has_status or has_fee or has_date):
                                st.error("❌ 檔案中必須包含『状态』、『运费』或『末条时间』至少其中一欄。")
                            else:
                                if has_fee:
                                    if df_track['物流運費'].dtype == object: df_track['物流運費'] = df_track['物流運費'].astype(str).str.replace(',', '')
                                    df_track['物流運費'] = pd.to_numeric(df_track['物流運費'], errors='coerce').fillna(0.0)
                                    
                                df_track = df_track.fillna("")
                                update_count = 0
                                
                                total_track_rows = len(df_track)
                                progress_bar_track = st.progress(0, text=f"準備依物流單號比對更新 {total_track_rows} 筆資料...")
                                
                                with get_db() as conn:
                                    cursor = conn.cursor()
                                    
                                    # 🌟 新增：紀錄這次上傳處理過的訂單，用來累加同訂單的多筆運費
                                    processed_orders = set()
                                    
                                    for i, (_, row) in enumerate(df_track.iterrows()):
                                        t_num = str(row['物流編號']).strip()
                                        
                                        # ⚠️ 極度重要防呆：如果單號是空的，直接跳過，避免搜尋到全部訂單
                                        if not t_num: 
                                            continue
                                        
                                        # 🌟 修改 1：改用 LIKE 模糊搜尋，只要包含該單號就能比對成功！
                                        cursor.execute("SELECT 訂單編號, 包裹應收, 商品成本, 物流運費_RMB FROM customer_orders WHERE 物流編號 LIKE ?", (f"%{t_num}%",))
                                        db_rows = cursor.fetchall() 
                                        
                                        if db_rows:
                                            for db_row in db_rows:
                                                oid, db_revenue, db_cost, db_shipping_rmb = db_row
                                                
                                                raw_status = str(row['狀態']).strip() if has_status and str(row['狀態']).strip() != "" else None
                                                
                                                status_map = {
                                                    '在途': '配送中', '待取件': '已送達待取', '签收': '簽收',
                                                    '退回': '退回', '退货上架': '已上架', '客诉': '客訴', '已重出': '已重出'
                                                }
                                                
                                                new_status = None
                                                if raw_status in status_map:
                                                    new_status = status_map[raw_status]
                                                elif raw_status in STATUS_LIST:
                                                    new_status = raw_status

                                                new_date = None
                                                if new_status == '簽收' and has_date and str(row['取貨日期']).strip() != "":
                                                    new_date = str(row['取貨日期']).strip()
                                                    
                                                # 🌟 修改 2：多包裹的智能運費累加邏輯 (防覆蓋)
                                                if has_fee and str(row['物流運費']).strip() != "":
                                                    current_row_fee = float(row['物流運費'])
                                                    
                                                    if oid not in processed_orders:
                                                        # 此訂單在「這份表格」第一次遇到：以表格運費為主
                                                        new_fee_rmb = current_row_fee
                                                        processed_orders.add(oid)
                                                    else:
                                                        # 發現多個包裹！讀取剛寫入的運費，並將第二筆以上的運費「加上去」
                                                        cursor.execute("SELECT 物流運費_RMB FROM customer_orders WHERE 訂單編號=?", (oid,))
                                                        latest_fee_row = cursor.fetchone()
                                                        latest_fee = float(latest_fee_row[0]) if latest_fee_row and latest_fee_row[0] is not None else 0.0
                                                        new_fee_rmb = latest_fee + current_row_fee
                                                else:
                                                    # 表格沒填運費：保留資料庫原有運費
                                                    new_fee_rmb = float(db_shipping_rmb if db_shipping_rmb is not None else 0.0)
                                                    
                                                new_fee_twd = new_fee_rmb * rate
                                                calc_ship = float(db_cost) + new_fee_twd
                                                calc_profit = float(db_revenue) - calc_ship
                                                
                                                updates, params = [], []
                                                if new_status: 
                                                    updates.append("取貨狀態=?")
                                                    params.append(new_status)
                                                    
                                                # 🌟 新增：如果狀態是簽收且有時間，寫入資料庫
                                                if new_date:
                                                    updates.append("取貨日期=?")
                                                    params.append(new_date)
                                                
                                                updates.append("物流運費_RMB=?"); params.append(new_fee_rmb)
                                                updates.append("物流運費=?"); params.append(new_fee_twd)
                                                updates.append("出貨成本=?"); params.append(calc_ship)
                                                updates.append("訂單損益=?"); params.append(calc_profit)
                                                
                                                params.append(oid)
                                                
                                                if updates:
                                                    cursor.execute(f"UPDATE customer_orders SET {', '.join(updates)} WHERE 訂單編號=?", tuple(params))
                                                    update_count += 1
                                                    
                                        progress_bar_track.progress((i + 1) / total_track_rows, text=f"更新進度：{i + 1} / {total_track_rows} 筆 (成功比對並更新: {update_count} 筆訂單)")
                                        
                                    conn.commit()
                                    
                                log_system_action("訂單明細", current_operator, "依物流單號更新", f"比對更新了 {update_count} 筆訂單，匯率設定：{rate}")
                                st.success(f"✅ 成功依物流單號為 {update_count} 筆訂單更新了運費、狀態與時間！")
                                time.sleep(1.5); st.rerun()
                    except Exception as e:
                        st.error(f"❌ 更新失敗，詳情：{str(e)}")
            # =========== exp3 結束 ===========

elif menu == "財務報表":
    st.title("📈 財務與利潤分析")
    if check_perm(role, "財務報表", "can_view"):
        # 👇 這裡把原本的 3 個頁籤增加為 4 個頁籤
        t1, t2, t3, t4 = st.tabs(["💰 收支總表", "🏆 品牌/單品毛利分析", "🚚 物流結款核對 (詳細版)", "💱 匯率與成本設定"])
        with t1: st.info("統整銷售收入與採購支出。")
        with t2: st.info("利用 FIFO (先進先出) 邏輯，精準計算各品牌與單品的實際利潤率。")
        
        # ==========================================
        # --- 新增的第 3 頁籤：物流結款核對詳細版 ---
        # ==========================================
        with t3:
            st.info("📥 上傳物流公司提供的結款收據，系統將為您逐筆交叉比對【簽收金額】、【手續費】、【人民幣】，並抓出漏結款的訂單！")
            
            c_rate, _ = st.columns([1, 3])
            logi_rate = c_rate.number_input("💵 本次核對匯率 (1 人民幣 = ? 台幣)", value=4.50, step=0.01, key="fin_logi_rate")
            
            uploaded_receipt = st.file_uploader("上傳物流結款明細 (需包含：物流編號、簽收金額、手續費、結款人民幣)", type=["csv", "xlsx"])
            
            if uploaded_receipt:
                try:
                    # 1. 讀取上傳的物流明細表
                    if uploaded_receipt.name.endswith('.csv'):
                        df_logi = pd.read_csv(uploaded_receipt, dtype=str)
                    else:
                        df_logi = pd.read_excel(uploaded_receipt, dtype=str, engine='openpyxl')
                        
                    df_logi.columns = df_logi.columns.astype(str).str.strip()
                    
                    # 智能欄位配對 (尋找物流表中的關鍵欄位)
                    col_mappings = {
                        '物流編號': ['物流編號', '运单号', '承运单号', '交货单号', '发货单号'],
                        '物流簽收金額': ['簽收金額', '代收金额', '签收金额', '包裹應收', '金额'],
                        '物流手續費': ['手續費', '手续费', '代收手续费'],
                        '物流結款人民幣': ['結款的人民幣', '结款金额', '应结人民币', '结算人民币', '結款人民幣']
                    }
                    
                    for target_col, aliases in col_mappings.items():
                        matched_cols = [c for c in df_logi.columns if c in aliases]
                        if matched_cols:
                            df_logi = df_logi.rename(columns={matched_cols[0]: target_col})
                            if len(matched_cols) > 1:
                                df_logi = df_logi.drop(columns=matched_cols[1:])
                                
                    if '物流編號' not in df_logi.columns:
                        st.error("❌ 檔案中找不到基準欄位『物流編號 / 运单号』，無法比對。")
                    else:
                        df_logi['物流編號'] = df_logi['物流編號'].astype(str).str.strip()
                        df_logi = df_logi[df_logi['物流編號'] != ""]
                        df_logi = df_logi[df_logi['物流編號'] != "nan"]
                        
                        # 轉換數值格式
                        for col in ['物流簽收金額', '物流手續費', '物流結款人民幣']:
                            if col in df_logi.columns:
                                df_logi[col] = pd.to_numeric(df_logi[col].astype(str).str.replace(',', ''), errors='coerce').fillna(0.0)
                            else:
                                df_logi[col] = 0.0 # 若檔案沒這欄位則補 0
                        
                        # 2. 從資料庫撈取系統內「已簽收」的單
                        with get_db() as conn:
                            df_db = pd.read_sql("SELECT 訂單編號, 物流編號, 包裹應收, 訂單日期 FROM customer_orders WHERE 取貨狀態='簽收'", conn)
                        
                        if df_db.empty:
                            st.warning("系統目前沒有狀態為『簽收』的訂單。")
                        else:
                            df_db['物流編號'] = df_db['物流編號'].astype(str).str.strip()
                            df_db['系統應收台幣'] = pd.to_numeric(df_db['包裹應收'], errors='coerce').fillna(0.0)
                            
                            # 系統自動計算：預估手續費與預估人民幣
                            import numpy as np
                            conditions = [df_db['系統應收台幣'] <= 9999, df_db['系統應收台幣'] >= 10000]
                            choices = [30, 160]
                            df_db['系統手續費'] = np.select(conditions, choices, default=30)
                            
                            df_db['系統結款_TWD'] = df_db['系統應收台幣'] - df_db['系統手續費']
                            df_db['系統結款_RMB'] = (df_db['系統結款_TWD'] / logi_rate).round(2)
                            
                            # 3. 開始交叉比對 (利用物流編號串接)
                            merged = pd.merge(df_db, df_logi, on='物流編號', how='left', indicator=True)
                            
                            # A. 雙方都有的單 (結款明細有、系統也有)
                            matched_df = merged[merged['_merge'] == 'both'].copy()
                            
                            # 計算差異
                            matched_df['金額差'] = matched_df['物流簽收金額'] - matched_df['系統應收台幣']
                            matched_df['手續費差'] = matched_df['物流手續費'] - matched_df['系統手續費']
                            matched_df['人民幣差'] = matched_df['物流結款人民幣'] - matched_df['系統結款_RMB']
                            
                            # B. 系統有簽收，但這次物流結款單「沒有」的單 (即未結款)
                            unsettled_df = merged[merged['_merge'] == 'left_only'].copy()
                            
                            # --- 畫面顯示區 ---
                            st.success(f"✅ 比對完成！您上傳的表格共 {len(df_logi)} 筆，成功與系統配對 {len(matched_df)} 筆訂單。")
                            
                            st.markdown("#### 🚨 比對異常清單 (需人工確認)")
                            st.caption("以下訂單的金額、手續費或結算人民幣與系統計算**不符** (容許 1 元內小數點誤差)：")
                            
                            # 找出有差異的單 (差額大於 1，過濾掉匯率小數點進位問題)
                            error_df = matched_df[
                                (matched_df['金額差'].abs() > 1) | 
                                (matched_df['手續費差'].abs() > 1) | 
                                (matched_df['人民幣差'].abs() > 1)
                            ][['訂單編號', '物流編號', '系統應收台幣', '物流簽收金額', '系統手續費', '物流手續費', '系統結款_RMB', '物流結款人民幣']]
                            
                            if error_df.empty:
                                st.info("🎉 太完美了！已配對的訂單中，所有金額與手續費皆與系統計算完全吻合！")
                            else:
                                st.error(f"⚠️ 發現 {len(error_df)} 筆帳務不符！")
                                st.dataframe(error_df, use_container_width=True, hide_index=True)
                                
                            st.divider()
                                
                            st.markdown("#### ⏳ 系統已簽收但【本次未結款】清單")
                            st.caption("以下是系統顯示已簽收，但「不在您上傳的這份結款單中」的訂單。")
                            # 為了避免顯示一兩年前早就結完的單，用拉桿控制顯示天數
                            days_filter = st.slider("顯示最近幾天內簽收的訂單？(避免舊單干擾)", min_value=7, max_value=90, value=30)
                            cutoff_date = pd.Timestamp.today() - pd.Timedelta(days=days_filter)
                            
                            unsettled_df['訂單日期_dt'] = pd.to_datetime(unsettled_df['訂單日期'], errors='coerce')
                            unsettled_recent = unsettled_df[unsettled_df['訂單日期_dt'] >= cutoff_date]
                            
                            if unsettled_recent.empty:
                                st.success(f"✅ 最近 {days_filter} 天內簽收的訂單，皆已出現在本次或歷史結款中了！")
                            else:
                                st.warning(f"📌 最近 {days_filter} 天內，共有 {len(unsettled_recent)} 筆已簽收但未在本次結款：")
                                show_unsettled = unsettled_recent[['訂單編號', '物流編號', '訂單日期', '系統應收台幣', '系統手續費', '系統結款_RMB']]
                                st.dataframe(show_unsettled, use_container_width=True, hide_index=True)
                                
                except Exception as e:
                    st.error(f"❌ 處理檔案時發生錯誤，請確認檔案格式是否正確。詳情：{str(e)}")
        
        with t4: st.info("設定當前人民幣/外幣匯率，讓進貨成本自動轉換為台幣。")
    else:
        st.error("🚫 您無權限訪問此模組")

elif menu == "權限管理":
    st.title("🔐 系統權限與帳號管理")
    current_operator = st.session_state.get('user', 'admin')
    
    if st.session_state.get('user') != 'admin' and role != "Admin": 
        st.error("🚫 僅限總管理員訪問此頁面")
        st.stop()
        
    # 🌟 擴充加入第四個分頁「📜 權限變更日誌」
    t_acct, t_perm, t_login_log, t_audit = st.tabs(["👥 帳號基本資料管理", "⚙️ 細部模組權限配置", "📜 帳號登入歷程紀錄", "📜 權限變更日誌"])
    
    # === Tab A: 帳號管理 ===
    with t_acct:
        st.info("管理員工帳號。您可以查看員工自訂的暱稱，並在『私密備註』欄位填寫僅限管理員可見的內部標記。")
        with get_db() as conn:
            df_users = pd.read_sql("SELECT username as 帳號, password as 密碼, nickname as 員工自訂暱稱, admin_remark as 管理員私密備註 FROM users", conn)
            df_users['密碼'] = df_users['密碼'].apply(decode_pw)
            
        edited_users = st.data_editor(
            df_users, num_rows="dynamic", use_container_width=True,
            column_config={
                "帳號": st.column_config.TextColumn("👤 登入帳號", required=True),
                "密碼": st.column_config.TextColumn("🔑 密碼", required=True),
                "員工自訂暱稱": st.column_config.TextColumn("📝 自訂暱稱"),
                "管理員私密備註": st.column_config.TextColumn("🔒 備註")
            }
        )
        
        if st.button("💾 儲存帳號基本資料", type="primary"):
            current_users = [u.strip() for u in edited_users['帳號'].dropna().astype(str).tolist() if u.strip() != '']
            
            if 'admin' not in current_users:
                st.error("❌ 系統防護：禁止刪除預設的 'admin' 總帳號！")
            else:
                try:
                    with get_db() as conn:
                        cursor = conn.cursor()
                        # 刪除被移除的帳號
                        placeholders = ','.join(['?'] * len(current_users))
                        cursor.execute(f"DELETE FROM users WHERE username NOT IN ({placeholders})", current_users)
                        
                        # 更新或新增帳號資料
                        for _, row in edited_users.iterrows():
                            u_name, u_pwd = str(row['帳號']).strip(), str(row['密碼']).strip()
                            u_nick = str(row['員工自訂暱稱']).strip() if pd.notna(row['員工自訂暱稱']) else ""
                            u_remark = str(row['管理員私密備註']).strip() if pd.notna(row['管理員私密備註']) else ""
                            if not u_name or u_name == 'nan': continue
                            
                            u_role = 'Admin' if u_name == 'admin' else 'CS'
                            
                            # 檢查是否存在，避免覆寫掉使用者的 last_active 狀態
                            cursor.execute("SELECT 1 FROM users WHERE username=?", (u_name,))
                            if cursor.fetchone():
                                cursor.execute("UPDATE users SET password=?, nickname=?, admin_remark=?, role=? WHERE username=?", 
                                               (encode_pw(u_pwd), u_nick, u_remark, u_role, u_name))
                            else:
                                cursor.execute("INSERT INTO users (username, password, nickname, admin_remark, role, last_active) VALUES (?, ?, ?, ?, ?, 0)", 
                                               (u_name, encode_pw(u_pwd), u_nick, u_remark, u_role))
                        conn.commit()
                        
                    # 🌟 寫入日誌
                    log_system_action("權限管理", current_operator, "修改帳號資料", f"更新了系統使用者帳號清單與資訊，當前共有 {len(current_users)} 個帳號")
                        
                    st.success("✅ 帳號資料更新成功！")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 儲存失敗發生異常：{str(e)}")

    # === Tab B: 細部權限設定 ===
    with t_perm:
        st.info("💡 針對指定員工設定各模組權限。若勾選『全選/全開』並按下儲存，系統將自動開啟該模組所有權限。")
        with get_db() as conn:
            user_list = pd.read_sql("SELECT username, nickname FROM users WHERE username != 'admin'", conn)
            
        if user_list.empty:
            st.warning("目前系統只有 admin 帳號，請先至『帳號基本資料管理』新增員工帳號。")
        else:
            user_options = [f"{r['username']} ({r['nickname']})" if r['nickname'] else r['username'] for _, r in user_list.iterrows()]
            selected_str = st.selectbox("🔍 請選擇要設定權限的帳號：", user_options)
            select_u = selected_str.split(" (")[0]
            
            modules = ["商品訊息", "商品庫存", "採購管理", "訂單明細", "財務報表"]
            with get_db() as conn:
                df_p = pd.read_sql("SELECT module, can_view, can_edit, can_upload, can_download FROM user_perms WHERE username=?", conn, params=(select_u,))
                
            perm_records = []
            for m in modules:
                match = df_p[df_p['module'] == m]
                if not match.empty:
                    perm_records.append({"模組": m, "👁️ 查看": bool(match.iloc[0]['can_view']), "✏️ 編輯": bool(match.iloc[0]['can_edit']), "📤 上傳": bool(match.iloc[0]['can_upload']), "📥 下載": bool(match.iloc[0]['can_download']), "🌟 全選/全開": False})
                else:
                    perm_records.append({"模組": m, "👁️ 查看": False, "✏️ 編輯": False, "📤 上傳": False, "📥 下載": False, "🌟 全選/全開": False})
                    
            df_edit_p = pd.DataFrame(perm_records)
            edited_p = st.data_editor(df_edit_p, hide_index=True, use_container_width=True, column_config={"模組": st.column_config.TextColumn(disabled=True)})
            
            if st.button(f"💾 儲存 {select_u} 的細部權限", type="primary"):
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM user_perms WHERE username=?", (select_u,))
                    
                    for _, row in edited_p.iterrows():
                        if row['🌟 全選/全開']:
                            v, e, u, d = True, True, True, True
                        else:
                            v, e, u, d = row['👁️ 查看'], row['✏️ 編輯'], row['📤 上傳'], row['📥 下載']
                            
                        cursor.execute("INSERT INTO user_perms (username, module, can_view, can_edit, can_upload, can_download) VALUES (?, ?, ?, ?, ?, ?)", (select_u, row['模組'], v, e, u, d))
                    conn.commit()
                
                # 🌟 寫入日誌
                log_system_action("權限管理", current_operator, "修改細部權限", f"更新了帳號 {select_u} 的各模組存取權限")
                    
                st.success(f"✅ 帳號 {select_u} 的顆粒化權限已生效！(被設定者需重新整理網頁方可套用)")
                time.sleep(1.5)
                st.rerun()
                
    # === Tab C: 登入歷程牆 ===
    with t_login_log:
        st.subheader("📋 員工系統登入審計安全日誌")
        st.write("此處會即時顯示所有使用者的登入軌跡，防範帳號遭盜用或異常跨國登入。")
        with get_db() as conn:
            # 取得原始資料
            df_login_data = pd.read_sql("SELECT username, login_time, ip, location, device FROM login_logs ORDER BY id DESC LIMIT 200", conn)
            
        if df_login_data.empty:
            st.info("✨ 目前系統尚無任何登入歷程紀錄。")
        else:
            # 🌟 1. 將 login_time 拆分為「日期」與「時間」兩欄
            df_login_data[['日期', '時間']] = df_login_data['login_time'].str.split(' ', n=1, expand=True)
            
            # 🌟 2. 自動判斷 User-Agent 轉換為易讀的「設備」與「瀏覽器環境」
            def parse_user_agent(ua):
                ua_str = str(ua).lower()
                
                # 判斷設備 OS
                if 'windows' in ua_str: os_name = 'Windows 電腦'
                elif 'mac os' in ua_str: os_name = 'Mac 電腦'
                elif 'android' in ua_str: os_name = 'Android 手機/平板'
                elif 'iphone' in ua_str: os_name = 'iPhone'
                elif 'ipad' in ua_str: os_name = 'iPad'
                elif 'linux' in ua_str: os_name = 'Linux'
                else: os_name = '未知設備'
                
                # 判斷瀏覽器
                if 'edg' in ua_str: browser = 'Edge'
                elif 'line' in ua_str: browser = 'LINE 內建'
                elif 'micromessenger' in ua_str: browser = '微信內建'
                elif 'chrome' in ua_str: browser = 'Chrome'
                elif 'safari' in ua_str and 'chrome' not in ua_str: browser = 'Safari'
                elif 'firefox' in ua_str: browser = 'Firefox'
                else: browser = '其他/未知'
                
                return pd.Series([os_name, browser])
            
            # 應用解析
            df_login_data[['設備', '瀏覽器環境']] = df_login_data['device'].apply(parse_user_agent)
            
            # 🌟 3. 整理最終要顯示的 DataFrame 欄位順序與中文命名
            df_display = df_login_data[['username', '日期', '時間', 'ip', 'location', '設備', '瀏覽器環境']].copy()
            df_display = df_display.rename(columns={
                'username': '帳號',
                'ip': 'IP 位址',
                'location': '位置'
            })
            
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            from io import BytesIO
            output_log = BytesIO()
            with pd.ExcelWriter(output_log, engine='openpyxl') as writer:
                df_display.to_excel(writer, index=False, sheet_name='Login_Logs')
            st.download_button(label="📥 下載完整登入歷程備份 (Excel 格式)", data=output_log.getvalue(), file_name=f"login_audit_logs_{time.strftime('%Y%m%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # === 🌟 全新 Tab D: 權限變更歷程 ===
    with t_audit:
        st.subheader("📜 系統權限變更日誌")
        st.write("此處會即時顯示所有關於「帳號增刪修改」與「模組權限調動」的操作歷程。")
        with get_db() as conn:
            df_perm_logs = pd.read_sql("SELECT timestamp as 操作時間, operator as 操作人員, action_type as 動作類別, details as 變動詳情說明 FROM system_logs WHERE module='權限管理' ORDER BY id DESC", conn)
            
        if df_perm_logs.empty:
            st.caption("✨ 目前尚無權限變更紀錄。")
        else:
            st.dataframe(df_perm_logs, use_container_width=True, hide_index=True)
