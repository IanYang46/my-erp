import streamlit as st
import sqlite3
import pandas as pd
import os
import time
import base64  # 🌟 改用 base64，這是可逆的編碼套件
import requests  # 🌟 新增：用於向 API 查詢 IP 的地理位置
import datetime
import extra_streamlit_components as stx

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
            [data-testid="stSidebar"] div[data-baseweb="input"] input, 
            [data-testid="stSidebar"] div[data-baseweb="select"] * {
                color: #0F172A !important;
            }
            [data-testid="stSidebar"] hr {
                border-color: #334155 !important;
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

# --- 2. 穩定的資料庫連線 ---
def get_db():
    return sqlite3.connect("powerful_group.db", timeout=30, check_same_thread=False)
    
# --- 3. 初始化資料庫與預設權限 ---
@st.cache_resource
def init_db_v7():  # 🌟 升級為 v7，確保系統重新整理時會建立新表
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. 建立系統核心表格
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
        
        # 🌟 安全擴充：為舊的 users 表格加入「暱稱」、「最後活躍時間」與「管理員私密備註」欄位
        cursor.execute("PRAGMA table_info(users)")
        cols = [info[1] for info in cursor.fetchall()]
        if 'nickname' not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN nickname TEXT DEFAULT ''")
        if 'last_active' not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN last_active REAL DEFAULT 0")
        if 'admin_remark' not in cols:
            cursor.execute("ALTER TABLE users ADD COLUMN admin_remark TEXT DEFAULT ''")
            
        cursor.execute('''CREATE TABLE IF NOT EXISTS permissions (role TEXT, module TEXT, can_view BOOLEAN, can_edit BOOLEAN, can_upload BOOLEAN, can_download BOOLEAN)''')
        
        # 細部權限設定表
        cursor.execute('''CREATE TABLE IF NOT EXISTS user_perms (
                            username TEXT, module TEXT, can_view BOOLEAN DEFAULT 0,
                            can_edit BOOLEAN DEFAULT 0, can_upload BOOLEAN DEFAULT 0,
                            can_download BOOLEAN DEFAULT 0, PRIMARY KEY (username, module))''')
        
        # 2. 商品資料表
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (編碼 TEXT PRIMARY KEY, 類別 TEXT, 品牌 TEXT, 名稱 TEXT, 備註 TEXT, 圖片路徑 TEXT)''')
        
        # 3. 庫存管理表
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, 編碼 TEXT, 倉庫位置 TEXT, 數量 INTEGER, 單支成本_RMB REAL, 採購廠商 TEXT, 採購金額_RMB REAL, 進貨日期 DATE)''')
        
        # 4. 匯率設定表
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL)''')
        cursor.execute("INSERT OR IGNORE INTO settings VALUES ('exchange_rate', 4.5)")
        
        # 5. 採購單與明細表
        cursor.execute('''CREATE TABLE IF NOT EXISTS procurement_orders (order_id TEXT PRIMARY KEY, date DATE, supplier TEXT, total_qty INTEGER, total_amount_rmb REAL, total_amount_twd REAL, warehouse TEXT, staff TEXT, status TEXT DEFAULT '待驗收')''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS procurement_items (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id TEXT, code TEXT, qty INTEGER, unit_price_rmb REAL, total_price_rmb REAL)''')

        # 6. 動態倉庫與日誌表
        cursor.execute('''CREATE TABLE IF NOT EXISTS warehouses (name TEXT PRIMARY KEY)''')
        cursor.execute("SELECT count(*) FROM warehouses")
        if cursor.fetchone()[0] == 0:
            for w in ['台灣黃興-商品', '東莞熙元-商品', '台灣黃興-樣品', '退換貨倉']:
                cursor.execute("INSERT OR IGNORE INTO warehouses (name) VALUES (?)", (w,))
                
        # 登入歷史紀錄表格
        cursor.execute('''CREATE TABLE IF NOT EXISTS login_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT, login_time TEXT, ip TEXT, location TEXT, device TEXT)''')
        
        # 7. 建立預設 Admin 帳號 
        cursor.execute("INSERT OR IGNORE INTO users (username, password, nickname, role) VALUES ('admin', ?, '總管理員', 'Admin')", (encode_pw('123456'),))
        
        # 🌟 8. 舊有的獨立日誌表 (保留給商品與庫存)
        cursor.execute('''CREATE TABLE IF NOT EXISTS product_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, operator TEXT, action_type TEXT, details TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, operator TEXT, action_type TEXT, details TEXT)''')
        
        # 🌟 9. 新增：全局系統操作日誌表 (供採購、訂單、權限等共用)
        cursor.execute('''CREATE TABLE IF NOT EXISTS system_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, module TEXT, operator TEXT, action_type TEXT, details TEXT)''')
        
        # 🌟 10. 全新：客戶訂單明細表 (涵蓋 17 個專屬欄位，訂單編號為唯一主鍵)
        cursor.execute('''CREATE TABLE IF NOT EXISTS customer_orders (
            訂單編號 TEXT PRIMARY KEY,
            訂單日期 DATE,
            訂單連結 TEXT,
            姓名 TEXT,
            電話 TEXT,
            門市 TEXT,
            店號 TEXT,
            品項內容 TEXT,
            下單總數 INTEGER,
            包裹應收 REAL,
            商品成本 REAL,
            物流運費 REAL,
            出貨成本 REAL,
            訂單損益 REAL,
            物流編號 TEXT,
            取貨狀態 TEXT DEFAULT '待出貨',
            取貨日期 DATE
        )''')
        
        # 🌟 11. 安全動態擴充：為舊的 customer_orders 表格加入「信箱」、「顧客備註」、「商家備註」
        cursor.execute("PRAGMA table_info(customer_orders)")
        order_cols = [info[1] for info in cursor.fetchall()]
        if '信箱' not in order_cols:
            cursor.execute("ALTER TABLE customer_orders ADD COLUMN 信箱 TEXT DEFAULT ''")
        if '顧客備註' not in order_cols:
            cursor.execute("ALTER TABLE customer_orders ADD COLUMN 顧客備註 TEXT DEFAULT ''")
        if '商家備註' not in order_cols:
            cursor.execute("ALTER TABLE customer_orders ADD COLUMN 商家備註 TEXT DEFAULT ''")

        conn.commit()
        
init_db_v7()

# --- 日誌自動寫入工具群 ---
def log_inventory_change(operator, action_type, details):
    with get_db() as conn:
        conn.execute("INSERT INTO inventory_logs (timestamp, operator, action_type, details) VALUES (datetime('now', 'localtime'), ?, ?, ?)", (operator, action_type, details))
        conn.commit()
        
def log_product_change(operator, action_type, details):
    with get_db() as conn:
        conn.execute("INSERT INTO product_logs (timestamp, operator, action_type, details) VALUES (datetime('now', 'localtime'), ?, ?, ?)", (operator, action_type, details))
        conn.commit()

def log_system_action(module, operator, action_type, details):
    with get_db() as conn:
        conn.execute("INSERT INTO system_logs (timestamp, module, operator, action_type, details) VALUES (datetime('now', 'localtime'), ?, ?, ?, ?)", (module, operator, action_type, details))
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
            conn.execute("UPDATE users SET last_active = 0 WHERE username = ?", (username_to_clear,))
            conn.commit()
        st.warning("⚠️ 由於長時間未操作，為保護系統安全，已為您自動登出。")
        time.sleep(2)
        st.rerun()
    else:
        # 有任何點擊或切換模組的短時間操作，刷新 Session 暫存，並立刻回寫資料庫存檔
        st.session_state['last_active'] = current_time
        with get_db() as conn:
            conn.execute("UPDATE users SET last_active = ? WHERE username = ?", (current_time, st.session_state['user']))
            conn.commit()

# 2. 狀況 B：若網頁剛被重開 (Session 暫存全空)，嘗試由 Cookie 與資料庫時間核對進行安全登入
if 'logged_in' not in st.session_state:
    auto_login_user = cookie_manager.get(cookie="erp_auto_login")
    
    # 🌟 偵錯提示：如果 Cookie 抓不到，嘗試強迫瀏覽器重新整理一次
    if auto_login_user:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role, nickname, last_active FROM users WHERE username = ?", (auto_login_user,))
            res = cursor.fetchone()
            if res:
                user_role, user_nick, db_last_active = res[0], res[1], (res[2] if res[2] else 0)
                
                if time.time() - db_last_active < TIMEOUT_SECONDS:
                    cursor.execute("SELECT module, can_view, can_edit, can_upload, can_download FROM user_perms WHERE username=?", (auto_login_user,))
                    perms_data = cursor.fetchall()
                    perm_dict = {row[0]: {'can_view': bool(row[1]), 'can_edit': bool(row[2]), 'can_upload': bool(row[3]), 'can_download': bool(row[4])} for row in perms_data}
                    
                    st.session_state.update({
                        'logged_in': True, 'role': user_role, 'user': auto_login_user, 
                        'nickname': user_nick if user_nick else auto_login_user, 'perms': perm_dict,
                        'last_active': time.time()
                    })
                    conn.execute("UPDATE users SET last_active = ? WHERE username = ?", (time.time(), auto_login_user))
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
                    cursor.execute("SELECT role, nickname FROM users WHERE username=? AND password=?", (user, encode_pw(pw)))
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
                    except sqlite3.IntegrityError:
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
    st.title("🏠 系統首頁 (Dashboard)")
    st.write("這裡是未來的數據儀表板，登入後一眼掌握公司營運狀況。")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("本月總營業額", "---")
    c2.metric("待處理訂單", "---")
    c3.metric("低於安全庫存商品", "---")
    c4.metric("本月採購支出", "---")

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
                       IFNULL(SUM(i.數量), 0) as 總庫存, IFNULL(SUM(i.採購金額_RMB), 0) as 總採購金額_RMB, AVG(i.單支成本_RMB) as 平均成本_RMB
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
                    df_raw_inv = pd.read_sql("SELECT i.id as 流水號, i.編碼, p.名稱 as 商品名稱, i.倉庫位置, i.數量, i.單支成本_RMB as '單支成本(RMB)', i.採購廠商, i.進貨日期 FROM inventory i LEFT JOIN products p ON i.編碼 = p.編碼 ORDER BY i.id DESC", conn)
                    
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

    # 🌟 1. 取得資料庫資料
    with get_db() as conn:
        df_orders = pd.read_sql("SELECT * FROM customer_orders ORDER BY 訂單日期 DESC", conn)

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

        def clean_and_preview(val):
            if pd.isna(val) or str(val).strip() in ['nan', 'None']: return ""
            return str(val)
        df_orders['品項內容_原始'] = df_orders['品項內容'].apply(clean_and_preview)
        df_orders['品項預覽'] = df_orders['品項內容_原始'].apply(lambda x: x.replace('\n', ' ｜ '))
        
        # 確保財務欄位為數值型態
        for col in ['包裹應收', '商品成本', '物流運費', '出貨成本', '訂單損益']:
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
    time_filter = c_time.selectbox("📅 選擇統計區間", ["全部", "今日", "本月", "本季", "今年", "自訂區間"])
    
    df_dash = df_orders.copy()
    if not df_dash.empty:
        df_dash['訂單日期_dt'] = pd.to_datetime(df_dash['訂單日期'], errors='coerce')
        now = pd.Timestamp.today()
        
        if time_filter == "今日": df_dash = df_dash[df_dash['訂單日期_dt'].dt.date == now.date()]
        elif time_filter == "本月": df_dash = df_dash[(df_dash['訂單日期_dt'].dt.year == now.year) & (df_dash['訂單日期_dt'].dt.month == now.month)]
        elif time_filter == "本季":
            current_quarter = (now.month - 1) // 3 + 1
            df_dash = df_dash[(df_dash['訂單日期_dt'].dt.year == now.year) & (df_dash['訂單日期_dt'].dt.quarter == current_quarter)]
        elif time_filter == "今年": df_dash = df_dash[df_dash['訂單日期_dt'].dt.year == now.year]
        elif time_filter == "自訂區間":
            dates = c_custom.date_input("選擇自訂日期區間", [])
            if len(dates) == 2: df_dash = df_dash[(df_dash['訂單日期_dt'].dt.date >= dates[0]) & (df_dash['訂單日期_dt'].dt.date <= dates[1])]
    
    total_orders = len(df_dash)
    total_revenue = df_dash['包裹應收'].sum() if not df_dash.empty else 0
    total_cost = df_dash['商品成本'].sum() if not df_dash.empty else 0
    total_shipping = df_dash['物流運費'].sum() if not df_dash.empty else 0
    total_est_profit = df_dash['訂單損益'].sum() if not df_dash.empty else 0
    
    picked_up = len(df_dash[df_dash['取貨狀態'] == '已取貨']) if not df_dash.empty else 0
    returned = len(df_dash[df_dash['取貨狀態'] == '退換貨處理中']) if not df_dash.empty else 0
    cancelled = len(df_dash[df_dash['取貨狀態'] == '取消']) if not df_dash.empty else 0
    unclaimed = len(df_dash[df_dash['取貨狀態'] == '未取退回']) if not df_dash.empty else 0
    
    actual_profit = 0
    if not df_dash.empty:
        profit_from_picked = df_dash[df_dash['取貨狀態'] == '已取貨']['訂單損益'].sum()
        loss_from_unclaimed = df_dash[df_dash['取貨狀態'] == '未取退回']['物流運費'].sum()
        actual_profit = profit_from_picked - loss_from_unclaimed

    st.markdown("""
    <style>
    div[data-testid="metric-container"] {
        background-color: #f8f9fa; border: 1px solid #e9ecef; padding: 10px; border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("📦 總訂單數", f"{total_orders:,}")
    m2.metric("💰 總營業額", f"${total_revenue:,.0f}")
    m3.metric("🛒 總成本", f"${total_cost:,.0f}")
    m4.metric("🚚 總運費", f"${total_shipping:,.0f}")
    m5.metric("📈 總預估利潤", f"${total_est_profit:,.0f}")
    
    m6, m7, m8, m9, m10 = st.columns(5)
    m6.metric("✅ 總取件數", f"{picked_up:,}")
    m7.metric("❌ 總未取退回", f"{unclaimed:,}")
    m8.metric("🔄 總退貨數", f"{returned:,}")
    m9.metric("🚫 總取消數", f"{cancelled:,}")
    m10.metric("💎 總實際利潤", f"${actual_profit:,.0f}", help="實際利潤 = (已取貨的訂單損益) - (未取退回所損失的物流運費)")

    st.divider()
    
    can_edit = check_perm(role, "訂單明細", "can_edit")
    t1, t2 = st.tabs(["📄 訂單總表與追蹤", "📥 批次匯入與建檔"])

    with t1:
        st.info("💡 **自動防護偵測**：若「姓名」、「電話」或「信箱」欄位呈現橘黃底色，代表該顧客在系統內有 **2筆以上** 紀錄，方便一眼識別常客或惡意未取顧客。若要查看備註與信箱，請開啟上方「展開顯示所有詳細欄位」。")

        if df_orders.empty:
            st.warning("目前尚無任何訂單資料。請至「批次匯入與建檔」上傳 Excel/CSV。")

        c_search, c_status, c_toggle = st.columns([2, 1, 1.2])
        with c_search: search_kw = st.text_input("🔍 搜尋訂單 (輸入姓名、電話、信箱或單號)", "")
        with c_status: status_filter = st.selectbox("📌 狀態篩選", ["全部", "待出貨", "配送中", "已抵達", "已取貨", "未取退回", "取消", "退換貨處理中"])
        with c_toggle:
            st.write(""); st.write("")
            show_all_cols = st.toggle("🔍 展開顯示所有詳細欄位", value=False)

        df_display = df_orders.copy()
        if not df_display.empty:
            if status_filter != "全部": df_display = df_display[df_display['取貨狀態'] == status_filter]
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
            "訂單編號": st.column_config.TextColumn("訂單編號", disabled=True),
            "訂單連結": st.column_config.LinkColumn("🔗 訂單連結"),
            "包裹應收": st.column_config.NumberColumn("包裹應收", format="$ %.0f"),
            "商品成本": st.column_config.NumberColumn("商品成本", format="$ %.0f"),
            "物流運費": st.column_config.NumberColumn("物流運費", format="$ %.0f"),
            "出貨成本": st.column_config.NumberColumn("出貨成本", format="$ %.0f", disabled=True),
            "訂單損益": st.column_config.NumberColumn("訂單損益", format="$ %.0f", disabled=True),
            "下單總數": st.column_config.NumberColumn("下單總數", step=1),
            "取貨狀態": st.column_config.SelectboxColumn("狀態", options=["待出貨", "配送中", "已抵達", "已取貨", "未取退回", "取消", "退換貨處理中"]),
            "品項預覽": st.column_config.TextColumn("📦 品項內容 (預覽)", disabled=True),
            "信箱": st.column_config.TextColumn("📧 信箱"),
            "顧客備註": st.column_config.TextColumn("👤 顧客備註"),
            "商家備註": st.column_config.TextColumn("🏪 商家備註")
        }

        if show_all_cols:
            display_cols = ["🗑️ 勾選", "訂單日期", "訂單編號", "訂單連結", "姓名", "電話", "信箱", "門市", "店號", "品項預覽", "下單總數", "包裹應收", "商品成本", "物流運費", "出貨成本", "訂單損益", "物流編號", "取貨狀態", "取貨日期", "顧客備註", "商家備註"]
        else:
            # 預設把信箱、顧客備註、商家備註拿掉，讓它們「縮起來」
            display_cols = ["🗑️ 勾選", "訂單編號", "訂單日期", "姓名", "電話", "品項預覽", "包裹應收", "出貨成本", "訂單損益", "物流編號", "取貨狀態"]

        # 🚀 終極解決方案：不再與 Streamlit 的底層 CSS 渲染機制打架
        # 改用我們已經算好的 is_repeat，轉換成一個極度顯眼的專屬標籤欄位
        if not df_display.empty:
            df_display['⚠️ 警示'] = df_display['is_repeat'].apply(lambda x: '🚨 重複' if x else '')

        if show_all_cols:
            display_cols = ["🗑️ 勾選", "⚠️ 警示", "訂單日期", "訂單編號", "訂單連結", "姓名", "電話", "信箱", "門市", "店號", "品項預覽", "下單總數", "包裹應收", "商品成本", "物流運費", "出貨成本", "訂單損益", "物流編號", "取貨狀態", "取貨日期", "顧客備註", "商家備註"]
        else:
            # 預設把信箱、顧客備註、商家備註拿掉，讓它們「縮起來」
            display_cols = ["🗑️ 勾選", "⚠️ 警示", "訂單編號", "訂單日期", "姓名", "電話", "品項預覽", "包裹應收", "出貨成本", "訂單損益", "物流編號", "取貨狀態"]

        if not df_display.empty:
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
            c_save, c_del = st.columns(2)
            to_delete = edited_orders[edited_orders["🗑️ 勾選"] == True]['訂單編號'].tolist() if not edited_orders.empty and "🗑️ 勾選" in edited_orders.columns else []

            with c_save:
                if st.button("💾 儲存上方總表狀態變更", type="primary", use_container_width=True):
                    try:
                        with get_db() as conn:
                            cursor = conn.cursor()
                            for _, row in edited_orders.iterrows():
                                if pd.isna(row['訂單編號']) or str(row['訂單編號']).strip() == "": continue 
                                row = row.fillna({'下單總數': 0, '包裹應收': 0.0, '商品成本': 0.0, '物流運費': 0.0})
                                
                                calc_ship_cost = float(row['商品成本']) + float(row['物流運費'])
                                calc_profit = float(row['包裹應收']) - calc_ship_cost
                                
                                cursor.execute("""
                                    UPDATE customer_orders SET 
                                    訂單日期=?, 訂單連結=?, 姓名=?, 電話=?, 信箱=?, 門市=?, 店號=?, 
                                    下單總數=?, 包裹應收=?, 商品成本=?, 物流運費=?, 出貨成本=?, 訂單損益=?, 
                                    物流編號=?, 取貨狀態=?, 取貨日期=?, 顧客備註=?, 商家備註=?
                                    WHERE 訂單編號=?
                                """, (
                                    str(row.get('訂單日期', '')), str(row.get('訂單連結', '')),
                                    str(row.get('姓名', '')), str(row.get('電話', '')), str(row.get('信箱', '')),
                                    str(row.get('門市', '')), str(row.get('店號', '')),
                                    int(row['下單總數']), float(row['包裹應收']), float(row['商品成本']),
                                    float(row['物流運費']), calc_ship_cost, calc_profit, 
                                    str(row.get('物流編號', '')), str(row.get('取貨狀態', '待出貨')), str(row.get('取貨日期', '')),
                                    str(row.get('顧客備註', '')), str(row.get('商家備註', '')),
                                    str(row['訂單編號']).strip()
                                ))
                            conn.commit()
                        log_system_action("訂單明細", current_operator, "更新訂單資料", "透過總表儲存了訂單狀態與備註，自動重新核算損益")
                        st.success("✅ 總表狀態資料已成功保存！")
                        time.sleep(1); st.rerun()
                    except Exception as e:
                        st.error(f"❌ 儲存失敗：{str(e)}")

            with c_del:
                if len(to_delete) > 0:
                    if st.button(f"⚠️ 確認刪除已勾選的 {len(to_delete)} 筆訂單", type="primary", use_container_width=True):
                        try:
                            with get_db() as conn:
                                cursor = conn.cursor()
                                placeholders = ','.join(['?'] * len(to_delete))
                                cursor.execute(f"DELETE FROM customer_orders WHERE 訂單編號 IN ({placeholders})", tuple(to_delete))
                                conn.commit()
                            log_system_action("訂單明細", current_operator, "刪除訂單資料", f"刪除了 {len(to_delete)} 筆訂單")
                            st.success(f"✅ 成功刪除 {len(to_delete)} 筆訂單！")
                            time.sleep(1); st.rerun()
                        except Exception as e:
                            st.error(f"❌ 刪除失敗：{str(e)}")

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
                    
                    c1, c2, c3, c4, c5 = st.columns(5)
                    edit_date = c1.text_input("訂單日期", value=target_order.get('訂單日期', ''))
                    edit_name = c2.text_input("顧客姓名", value=target_order.get('姓名', ''))
                    edit_phone = c3.text_input("聯絡電話", value=target_order.get('電話', ''))
                    edit_email = c4.text_input("📧 聯絡信箱", value=target_order.get('信箱', ''))
                    edit_link = c5.text_input("訂單連結", value=target_order.get('訂單連結', ''))

                    c6, c7, c8, c9 = st.columns(4)
                    edit_store = c6.text_input("取件門市", value=target_order.get('門市', ''))
                    edit_store_id = c7.text_input("門市店號", value=target_order.get('店號', ''))
                    edit_logistics = c8.text_input("物流編號", value=target_order.get('物流編號', ''))
                    
                    status_opts = ["待出貨", "配送中", "已抵達", "已取貨", "未取退回", "取消", "退換貨處理中"]
                    current_status = target_order.get('取貨狀態', '待出貨')
                    if current_status not in status_opts: status_opts.append(current_status)
                    edit_status = c9.selectbox("取貨狀態", options=status_opts, index=status_opts.index(current_status))

                    st.markdown("##### 💰 金額與成本核算 (金額皆為台幣 TWD)")
                    c10, c11, c12, c13 = st.columns(4)
                    edit_qty = c10.number_input("下單總數", value=int(target_order.get('下單總數', 0)), step=1)
                    edit_revenue = c11.number_input("包裹應收", value=float(target_order.get('包裹應收', 0.0)), step=10.0)
                    edit_cost = c12.number_input("商品成本", value=float(target_order.get('商品成本', 0.0)), step=10.0)
                    edit_shipping = c13.number_input("物流運費", value=float(target_order.get('物流運費', 0.0)), step=10.0)
                    
                    db_ship_cost = float(target_order.get('出貨成本', 0.0))
                    db_profit = float(target_order.get('訂單損益', 0.0))
                    st.caption(f"📝 目前存檔狀態 👉 系統結算之出貨總成本：**{db_ship_cost:,.0f}** ｜ 訂單最終損益：**{db_profit:,.0f}**")

                    new_items = st.text_area("📦 品項內容 (支援直接在此處換行編輯)", value=target_order.get('品項內容_原始', ''), height=180)
                    
                    c14, c15 = st.columns(2)
                    edit_cust_note = c14.text_area("👤 顧客備註", value=target_order.get('顧客備註', ''))
                    edit_merch_note = c15.text_area("🏪 商家備註", value=target_order.get('商家備註', ''))

                    if can_edit:
                        if st.form_submit_button("💾 儲存這筆訂單的所有完整變更", type="primary", use_container_width=True):
                            try:
                                calc_single_ship_cost = edit_cost + edit_shipping
                                calc_single_profit = edit_revenue - calc_single_ship_cost
                                
                                with get_db() as conn:
                                    conn.execute("""
                                        UPDATE customer_orders SET 
                                        訂單日期=?, 姓名=?, 電話=?, 信箱=?, 訂單連結=?, 
                                        門市=?, 店號=?, 物流編號=?, 取貨狀態=?,
                                        下單總數=?, 包裹應收=?, 商品成本=?, 物流運費=?, 出貨成本=?, 訂單損益=?,
                                        品項內容=?, 顧客備註=?, 商家備註=?
                                        WHERE 訂單編號=?
                                    """, (
                                        edit_date, edit_name, edit_phone, edit_email, edit_link,
                                        edit_store, edit_store_id, edit_logistics, edit_status,
                                        edit_qty, edit_revenue, edit_cost, edit_shipping, calc_single_ship_cost, calc_single_profit,
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

    with t2:
        st.subheader("📥 批量導入外部訂單資料")
        if not check_perm(role, "訂單明細", "can_upload"):
            st.warning("🔒 您沒有上傳外部訂單的權限。")
        else:
            st.caption("💡 系統會自動過濾外部欄位並合併複數品項。若包含『信箱』、『顧客備註』、『商家備註』系統也會一併抓取匯入。")
            uploaded_order = st.file_uploader("選擇訂單檔案", type=["csv", "xlsx"], key="order_uploader")
            
            if uploaded_order and st.button("🚀 執行訂單匯入", type="primary"):
                try:
                    df_imp = pd.read_csv(uploaded_order) if uploaded_order.name.endswith('.csv') else pd.read_excel(uploaded_order, engine='openpyxl')
                    
                    col_mapping = {
                        '訂單編號': '訂單編號', '建立日期': '訂單日期', '顧客': '姓名', '產品': '品項內容',
                        '產品數量': '下單總數', '總計金額': '包裹應收', '顧客電話': '電話',
                        '信箱': '信箱', 'Email': '信箱', '顧客信箱': '信箱', 
                        '運送超商': '門市', '超商代號': '店號',
                        '顧客備註': '顧客備註', '買家備註': '顧客備註',
                        '商家備註': '商家備註', '賣家備註': '商家備註'
                    }
                    df_imp = df_imp.rename(columns=col_mapping)
                    
                    if '訂單編號' not in df_imp.columns:
                        st.error("❌ 匯入失敗：檔案中找不到『訂單編號』欄位。")
                    else:
                        df_imp = df_imp[df_imp['訂單編號'].astype(str).str.strip() != ""]
                        if '下單總數' in df_imp.columns: df_imp['下單總數'] = pd.to_numeric(df_imp['下單總數'], errors='coerce').fillna(0)
                        if '包裹應收' in df_imp.columns:
                            if df_imp['包裹應收'].dtype == object: df_imp['包裹應收'] = df_imp['包裹應收'].astype(str).str.replace(',', '')
                            df_imp['包裹應收'] = pd.to_numeric(df_imp['包裹應收'], errors='coerce').fillna(0.0)
                            
                        df_imp = df_imp.fillna("")
                        agg_funcs = {}
                        for col in df_imp.columns:
                            if col == '訂單編號': continue
                            elif col == '品項內容': agg_funcs[col] = lambda x: '\n'.join([f"• {str(i).strip()}" for i in x if str(i).strip() != ""])
                            elif col == '下單總數': agg_funcs[col] = 'sum'
                            else: agg_funcs[col] = 'first' 
                                
                        df_grouped = df_imp.groupby('訂單編號', as_index=False).agg(agg_funcs)

                        with get_db() as conn:
                            cursor = conn.cursor()
                            count = 0
                            for _, row in df_grouped.iterrows():
                                cursor.execute("""
                                    INSERT INTO customer_orders 
                                    (訂單編號, 訂單日期, 姓名, 電話, 信箱, 門市, 店號, 品項內容, 下單總數, 包裹應收, 商品成本, 物流運費, 出貨成本, 訂單損益, 物流編號, 取貨狀態, 取貨日期, 顧客備註, 商家備註)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0.0, 0.0, 0.0, '', '待出貨', '', ?, ?)
                                    ON CONFLICT(訂單編號) DO UPDATE SET
                                        訂單日期 = excluded.訂單日期,
                                        姓名 = excluded.姓名,
                                        電話 = excluded.電話,
                                        信箱 = excluded.信箱,
                                        門市 = excluded.門市,
                                        店號 = excluded.店號,
                                        品項內容 = excluded.品項內容,
                                        下單總數 = excluded.下單總數,
                                        包裹應收 = excluded.包裹應收,
                                        顧客備註 = excluded.顧客備註,
                                        商家備註 = excluded.商家備註;
                                """, (
                                    str(row['訂單編號']).strip(), str(row.get('訂單日期', '')), str(row.get('姓名', '')),
                                    str(row.get('電話', '')), str(row.get('信箱', '')), str(row.get('門市', '')), str(row.get('店號', '')),
                                    str(row.get('品項內容', '')), int(row.get('下單總數', 0)), float(row.get('包裹應收', 0.0)),
                                    str(row.get('顧客備註', '')), str(row.get('商家備註', ''))
                                ))
                                count += 1
                            conn.commit()
                            
                        log_system_action("訂單明細", current_operator, "匯入訂單資料", f"成功批次合併與匯入了 {count} 筆訂單，包含新欄位")
                        st.success(f"✅ 成功匯入並智能合併為 {count} 筆獨立訂單！")
                        time.sleep(1.5); st.rerun()
                except Exception as e:
                    st.error(f"❌ 匯入失敗，詳情：{str(e)}")

elif menu == "財務報表":
    st.title("📈 財務與利潤分析")
    if check_perm(role, "財務報表", "can_view"):
        t1, t2, t3 = st.tabs(["💰 收支總表", "🏆 品牌/單品毛利分析", "💱 匯率與成本設定"])
        with t1: st.info("統整銷售收入與採購支出。")
        with t2: st.info("利用 FIFO (先進先出) 邏輯，精準計算各品牌與單品的實際利潤率。")
        with t3: st.info("設定當前人民幣/外幣匯率，讓進貨成本自動轉換為台幣。")
    else: st.error("🚫 您無權限訪問此模組")

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
