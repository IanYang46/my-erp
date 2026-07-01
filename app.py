import streamlit as st
import sqlite3
import pandas as pd
import os
import time
import base64  # 🌟 改用 base64，這是可逆的編碼套件

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

# --- 2. 穩定的資料庫連線 ---
def get_db():
    return sqlite3.connect("powerful_group.db", timeout=30, check_same_thread=False)
    
# --- 3. 初始化資料庫與預設權限 ---
@st.cache_resource
def init_db_v3():  # 🌟 這裡改成 v3
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 🧨 強制刪除舊的錯誤表格 (這會清空舊的 hashlib 亂碼，並重置正確的表)
        cursor.execute("DROP TABLE IF EXISTS users")
        
        # 1. 建立系統核心表格
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS permissions (role TEXT, module TEXT, can_view BOOLEAN, can_edit BOOLEAN, can_upload BOOLEAN, can_download BOOLEAN)''')
        
        # 2. 商品資料表
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                            編碼 TEXT PRIMARY KEY, 
                            類別 TEXT, 
                            品牌 TEXT, 
                            名稱 TEXT, 
                            備註 TEXT, 
                            圖片路徑 TEXT)''')
        
        # 3. 庫存管理表
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            編碼 TEXT,
                            倉庫位置 TEXT,
                            數量 INTEGER,
                            單支成本_RMB REAL,
                            採購廠商 TEXT,
                            採購金額_RMB REAL,
                            進貨日期 DATE)''')
        
        # 4. 匯率設定表
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL)''')
        cursor.execute("INSERT OR IGNORE INTO settings VALUES ('exchange_rate', 4.5)")
        
        # 5. 採購單主表
        cursor.execute('''CREATE TABLE IF NOT EXISTS procurement_orders (
                            order_id TEXT PRIMARY KEY,
                            date DATE,
                            supplier TEXT,
                            total_qty INTEGER,
                            total_amount_rmb REAL,
                            total_amount_twd REAL,
                            warehouse TEXT,
                            staff TEXT,
                            status TEXT DEFAULT '待驗收')''')
                            
        # 6. 採購單明細表 
        cursor.execute('''CREATE TABLE IF NOT EXISTS procurement_items (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            order_id TEXT,
                            code TEXT,
                            qty INTEGER,
                            unit_price_rmb REAL,
                            total_price_rmb REAL)''')

        # 🌟 7. 【本次新增】：動態倉庫位置表
        cursor.execute('''CREATE TABLE IF NOT EXISTS warehouses (name TEXT PRIMARY KEY)''')
        cursor.execute("SELECT count(*) FROM warehouses")
        if cursor.fetchone()[0] == 0:
            default_whs = ['台灣黃興-商品', '東莞熙元-商品', '台灣黃興-樣品', '東莞熙元-樣品', '退換貨倉', '東莞熙元-待結款']
            for w in default_whs:
                cursor.execute("INSERT OR IGNORE INTO warehouses (name) VALUES (?)", (w,))
        
        # 8. 建立預設 Admin 帳號 
        cursor.execute("INSERT OR IGNORE INTO users VALUES ('admin', ?, 'Admin')", (encode_pw('123456'),))
        
        # 9. 初始化全新權限矩陣
        cursor.execute("SELECT count(*) FROM permissions")
        if cursor.fetchone()[0] == 0:
            modules = ["商品訊息", "商品庫存", "採購管理", "訂單明細", "財務報表"]
            roles = ["Admin", "Finance", "Shareholder", "CS"]
            for r in roles:
                v, e, u, d = (1, 1, 1, 1) if r == "Admin" else (0, 0, 0, 0)
                for m in modules:
                    cursor.execute("INSERT INTO permissions VALUES (?,?,?,?,?,?)", (r, m, v, e, u, d))
        
        conn.commit()
        
init_db_v2()

# --- 4. 權限檢查工具 ---
def check_perm(role_string, module, action=None):
    if str(role_string) == "Admin":
        return True
    return module in str(role_string)

# --- 5. 系統登入 ---
if 'logged_in' not in st.session_state:
    st.title("📦 強盛集團 | ERP 系統")
    
    mode = st.radio("請選擇模式", ["登入", "註冊"], horizontal=True)
    
    if mode == "登入":
        with st.form("login_form"):
            user = st.text_input("帳號")
            pw = st.text_input("密碼", type="password")
            if st.form_submit_button("登入"):
                with get_db() as conn:
                    cursor = conn.cursor()
                    # 🌟 比對時，將輸入的密碼 encode 後去跟資料庫比對
                    cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (user, encode_pw(pw)))
                    res = cursor.fetchone()
                    if res:
                        st.session_state.update({'logged_in': True, 'role': res[0], 'user': user})
                        st.rerun()
                    else:
                        st.error("帳號或密碼錯誤！")
                        
    else: 
        with st.form("register_form"):
            new_user = st.text_input("設定新帳號")
            new_pw = st.text_input("設定新密碼", type="password")
            confirm_pw = st.text_input("確認密碼", type="password")
            
            if st.form_submit_button("註冊"):
                if not new_user or not new_pw:
                    st.error("帳號與密碼不可為空！")
                elif new_pw != confirm_pw:
                    st.error("兩次密碼輸入不一致！")
                else:
                    try:
                        with get_db() as conn:
                            cursor = conn.cursor()
                            # 🌟 註冊時，將新密碼 encode 後存入
                            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                                           (new_user, encode_pw(new_pw), 'CS'))
                            conn.commit()
                            st.success(f"註冊成功！帳號【{new_user}】已建立，請切換至登入模式登入。")
                    except sqlite3.IntegrityError:
                        st.error("❌ 該帳號名稱已被註冊，請更換一個。")

    st.stop()

# --- 6. 側邊欄設計 ---
st.sidebar.title("🏢 強盛集團 ERP")
st.sidebar.info(f"👤 帳號: {st.session_state['user']} \n🔑 角色: {st.session_state['role']}")
if st.sidebar.button("登出系統", use_container_width=True): 
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()

menu = st.sidebar.radio(
    "請選擇功能模組：", 
    ["首頁", "商品訊息", "商品庫存", "採購管理", "訂單明細", "財務報表", "權限管理"],
    key="main_menu"
)
role = st.session_state['role']

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
    
    if check_perm(role, "商品訊息", "can_view"):
        tab1, tab2, tab3 = st.tabs(["📋 列表瀏覽與編輯", "➕ 新增商品", "📁 批次作業"])
        
        with tab1:
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
                    if selected_category != "全部":
                        filtered_df = filtered_df[filtered_df["類別"] == selected_category]
                    if selected_brand != "全部":
                        filtered_df = filtered_df[filtered_df["品牌"] == selected_brand]
                    
                    st.divider()
                    st.caption(f"📊 顯示結果：共找到 {len(filtered_df)} 筆符合條件的商品")
                    
                    if filtered_df.empty:
                        st.warning("沒有符合此篩選條件的商品，請嘗試其他組合。")
                    else:
                        for _, row in filtered_df.iterrows():
                            with st.container(border=True):
                                img_col, info_col, remark_col, action_col = st.columns([1.5, 3, 4.5, 1.5])
                                
                                if row['圖片路徑'] and os.path.exists(row['圖片路徑']):
                                    img_col.image(row['圖片路徑'], width=120)
                                else:
                                    img_col.write("無圖")
                                    
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
                                conn.execute("UPDATE products SET 類別=?, 品牌=?, 名稱=?, 備註=?, 圖片路徑=? WHERE 編碼=?",
                                             (edit_cat, edit_brand, edit_name, edit_remark, new_path, edit_code))
                                conn.commit()
                            
                            st.success(f"✅ 商品 {edit_code} 資料已成功更新！")
                            st.session_state['edit_item_code'] = None
                            time.sleep(1.5)
                            st.rerun()
                
        with tab2:
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
                                    conn.execute("INSERT INTO products (編碼, 類別, 品牌, 名稱, 備註, 圖片路徑) VALUES (?,?,?,?,?,?)",
                                                 (code, category, brand, name, remark, path))
                                    conn.commit()
                                
                                st.success(f"🎉 成功新增商品：【{code}】 {name}！")
                                time.sleep(1.5)
                                st.rerun()
                            except sqlite3.IntegrityError:
                                st.error(f"❌ 錯誤：編碼 【{code}】 已經存在！如需修改請至『列表瀏覽』點擊編輯。")
            else:
                st.error("🚫 您沒有編輯商品的權限")

        with tab3:
            st.subheader("📥 批量下載完整商品表")
            if check_perm(role, "商品訊息", "can_download"):
                with get_db() as conn:
                    df_all = pd.read_sql("SELECT 編碼, 類別, 品牌, 名稱, 備註 FROM products ORDER BY 編碼 ASC", conn)
                
                from io import BytesIO
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_all.to_excel(writer, index=False, sheet_name='Sheet1')
                excel_data = output.getvalue()
                
                st.download_button(
                    label="💾 下載商品清單 (Excel格式)",
                    data=excel_data,
                    file_name="products.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            st.divider()
            st.subheader("📤 批量上傳商品資料")
            if check_perm(role, "商品訊息", "can_upload"):
                uploaded_file = st.file_uploader("選擇上傳檔案 (支援 CSV 或 Excel)", type=["csv", "xlsx"])
                if uploaded_file and st.button("🚀 執行批量匯入", type="primary"):
                    try:
                        if uploaded_file.name.endswith('.csv'):
                            df_new = pd.read_csv(uploaded_file)
                        else:
                            df_new = pd.read_excel(uploaded_file, engine='openpyxl')
                            
                        df_insert = df_new[["編碼", "類別", "品牌", "名稱", "備註"]].fillna("---")
                        with get_db() as conn:
                            cursor = conn.cursor()
                            for _, row in df_insert.iterrows():
                                cursor.execute("SELECT 圖片路徑 FROM products WHERE 編碼=?", (str(row["編碼"]),))
                                img_res = cursor.fetchone()
                                existing_img = img_res[0] if img_res else ""
                                cursor.execute("INSERT OR REPLACE INTO products (編碼, 類別, 品牌, 名稱, 備註, 圖片路徑) VALUES (?,?,?,?,?,?)",
                                               (str(row["編碼"]), str(row["類別"]), str(row["品牌"]), str(row["名稱"]), str(row["備註"]), existing_img))
                            conn.commit()
                        st.success("✅ 批量商品資料匯入完成！")
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 匯入錯誤：{str(e)}")
    else:
        st.error("🚫 您無權限訪問此模組")

elif menu == "商品庫存":
    st.title("🏭 商品庫存與倉庫管理")

    # 取得最新匯率與倉庫名單
    with get_db() as conn:
        rate = conn.execute("SELECT value FROM settings WHERE key='exchange_rate'").fetchone()[0]
        wh_df = pd.read_sql("SELECT name FROM warehouses", conn)
        wh_list = wh_df['name'].tolist()
    
    new_rate = st.sidebar.number_input("當前人民幣匯率 (RMB to TWD)", value=rate, step=0.01)
    if st.sidebar.button("更新匯率"):
        with get_db() as conn:
            conn.execute("UPDATE settings SET value=? WHERE key='exchange_rate'", (new_rate,))
            conn.commit()
        st.rerun()

    if check_perm(role, "商品庫存", "can_view"):
        tab_inv, tab_wh = st.tabs(["📊 庫存總覽與查詢", "🏢 倉庫位置管理"])
        
        # ==========================================
        # --- Tab 1: 庫存總覽 (含圖片與倉庫篩選) ---
        # ==========================================
        with tab_inv:
            # 倉庫篩選器
            c_wh, c_status = st.columns(2)
            selected_wh = c_wh.selectbox("🔍 篩選特定倉庫 (查看單一倉庫庫存)", ["所有倉庫"] + wh_list)
            show_type = c_status.radio("篩選庫存狀態", ["顯示所有", "僅顯示有庫存", "僅顯示缺貨"], horizontal=True)
            
            with get_db() as conn:
                # 依據選擇的倉庫動態改變 SQL 查詢
                query = """
                SELECT p.圖片路徑, p.編碼, p.名稱, p.類別, p.品牌, 
                       IFNULL(SUM(i.數量), 0) as 總庫存,
                       IFNULL(SUM(i.採購金額_RMB), 0) as 總採購金額_RMB,
                       AVG(i.單支成本_RMB) as 平均成本_RMB
                FROM products p
                LEFT JOIN inventory i ON p.編碼 = i.編碼
                """
                params = []
                if selected_wh != "所有倉庫":
                    query += " AND i.倉庫位置 = ?"
                    params.append(selected_wh)
                    
                query += " GROUP BY p.編碼 ORDER BY p.編碼 ASC"
                df = pd.read_sql(query, conn, params=params)
            
            # 計算台幣金額
            df["總庫存金額_RMB"] = df["總採購金額_RMB"]
            df["總庫存金額_TWD"] = df["總庫存金額_RMB"] * new_rate
            df["平均成本_TWD"] = df["平均成本_RMB"] * new_rate
            
            # 本地圖片轉 Base64 引擎 (讓 DataFrame 可以直接渲染圖片)
            def get_image_base64(path):
                if pd.isna(path) or not path: return None
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                        return f"data:image/jpeg;base64,{encoded}"
                return None
            
            df['商品圖片'] = df['圖片路徑'].apply(get_image_base64)
            
            # 調整欄位順序，並套用缺貨篩選
            cols = ['商品圖片', '編碼', '名稱', '類別', '品牌', '總庫存', '平均成本_RMB', '平均成本_TWD', '總庫存金額_RMB', '總庫存金額_TWD']
            filtered_df = df[cols].copy()
            
            if show_type == "僅顯示有庫存": filtered_df = filtered_df[filtered_df["總庫存"] > 0]
            elif show_type == "僅顯示缺貨": filtered_df = filtered_df[filtered_df["總庫存"] <= 0]
            
            st.dataframe(
                filtered_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "商品圖片": st.column_config.ImageColumn("圖片", help="商品實體圖"),
                    "總庫存": st.column_config.NumberColumn("總庫存", format="%d 支"),
                    "平均成本_RMB": st.column_config.NumberColumn("單支成本 (¥)", format="¥ %.2f"),
                    "平均成本_TWD": st.column_config.NumberColumn("單支成本 (NT$)", format="$ %.2f"),
                }
            )
            
            # 匯出報表
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # 匯出時把 Base64 圖片那欄拿掉，以免 Excel 壞掉
                export_df = filtered_df.drop(columns=['商品圖片'])
                export_df.to_excel(writer, index=False, sheet_name='Inventory')
            
            st.download_button(
                label="💾 下載當前庫存報表 (Excel)",
                data=output.getvalue(),
                file_name=f"inventory_{selected_wh}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # ==========================================
        # --- Tab 2: 倉庫位置動態管理 ---
        # ==========================================
        with tab_wh:
            st.subheader("🏢 系統倉庫位置管理")
            st.write("您可以在此自由新增、修改或刪除倉庫位置，這些設定會同步更新至『採購管理』的入庫選項中。")
            
            with get_db() as conn:
                df_wh_edit = pd.read_sql("SELECT name as 倉庫名稱 FROM warehouses", conn)
                
            edited_wh = st.data_editor(
                df_wh_edit, 
                num_rows="dynamic",
                use_container_width=True,
                column_config={"倉庫名稱": st.column_config.TextColumn("📦 倉庫名稱 (必填，不可重複)", required=True)}
            )
            
            if st.button("💾 儲存所有倉庫設定", type="primary"):
                current_whs = edited_wh['倉庫名稱'].dropna().astype(str).tolist()
                current_whs = [w.strip() for w in current_whs if w.strip() != '']
                
                if not current_whs:
                    st.error("❌ 系統至少需要保留一個倉庫！")
                else:
                    try:
                        with get_db() as conn:
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM warehouses")
                            for w in current_whs:
                                cursor.execute("INSERT INTO warehouses (name) VALUES (?)", (w,))
                            conn.commit()
                        st.success("✅ 倉庫名單已成功更新！系統將自動重載。")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 儲存失敗：{str(e)}")
    else:
        st.error("🚫 您無權限訪問此模組")

elif menu == "採購管理":
    st.title("🛒 採購與進貨管理系統")
    
    if not check_perm(role, "採購管理", "can_view"):
        st.error("🚫 您無權限訪問此模組")
        st.stop()

    # 取得當前系統即時台幣匯率，用來自動換算台幣總金額
    with get_db() as conn:
        rate = conn.execute("SELECT value FROM settings WHERE key='exchange_rate'").fetchone()[0]

    tab1, tab2, tab3 = st.tabs(["📝 新增採購單", "📋 採購單歷史與點收驗收", "📊 批次作業 (導入/導出)"])

    # ==========================================
    # --- Tab 1: 新增採購單 (連結商品訊息資料) ---
    # ==========================================
    with tab1:
        st.subheader("✍️ 建立新採購單單據")
        
        # 🌟 這裡修改了！同時撈取商品庫跟剛剛新增的「倉庫清單」，供下拉選取
        with get_db() as conn:
            prod_df = pd.read_sql("SELECT 編碼, 名稱 FROM products ORDER BY 編碼 ASC", conn)
            wh_df = pd.read_sql("SELECT name FROM warehouses", conn) # 撈取動態倉庫
            
        valid_product_codes = prod_df['編碼'].tolist()
        valid_warehouses = wh_df['name'].tolist() # 轉換成清單

        if not valid_product_codes:
            st.warning("⚠️ 目前商品訊息庫中沒有任何商品資料，請先至『商品訊息』建立基本商品再進行採購。")
        elif not valid_warehouses:
            st.warning("⚠️ 系統偵測不到任何倉庫！請先至『商品庫存』分頁建立至少一個倉庫位置。")
        else:
            # 填寫單據主表基本欄位
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            date_input = col_m1.date_input("採購日期")
            supplier_input = col_m2.text_input("採購廠商 (供應商名稱)", placeholder="例如：法國香氛總倉")
            
            # 🌟 這裡修改了！將原本寫死的陣列改成連動的 valid_warehouses
            warehouse_input = col_m3.selectbox("購入的倉庫", valid_warehouses)
            
            staff_input = col_m4.text_input("採購人員", value=st.session_state.get('user', 'admin'))

            st.write("📌 **請於下方表格中新增採購品項及金額：**")
            
            # 使用 Session State 初始化動態多品項採購編輯器
            if "po_editor_df" not in st.session_state:
                st.session_state.po_editor_df = pd.DataFrame(columns=["商品編碼", "數量", "人民幣單價"])

            edited_items = st.data_editor(
                st.session_state.po_editor_df,
                num_rows="dynamic",
                use_container_width=True,
                key="po_items_editor",
                column_config={
                    "商品編碼": st.column_config.SelectboxColumn("📦 選擇商品編碼", options=valid_product_codes, required=True),
                    "數量": st.column_config.NumberColumn("🔢 採購數量", min_value=1, step=1, default=1),
                    "人民幣單價": st.column_config.NumberColumn("💰 人民幣單價 (RMB)", min_value=0.0, step=0.01, default=0.0)
                }
            )

            # 計算即時總體金額數據
            if not edited_items.empty:
                edited_items['數量'] = pd.to_numeric(edited_items['數量']).fillna(0).astype(int)
                edited_items['人民幣單價'] = pd.to_numeric(edited_items['人民幣單價']).fillna(0.0)
                edited_items['總金額_RMB'] = edited_items['數量'] * edited_items['人民幣單價']
                
                total_qty = int(edited_items['數量'].sum())
                total_rmb = float(edited_items['總金額_RMB'].sum())
                total_twd = total_rmb * rate
            else:
                total_qty, total_rmb, total_twd = 0, 0.0, 0.0

            # 儀表板看板顯示本次單據總計
            st.divider()
            sum_c1, sum_c2, sum_c3 = st.columns(3)
            sum_c1.metric("📦 總採購數量", f"{total_qty} 支")
            sum_c2.metric("¥ 人民幣總金額", f"{total_rmb:,.2f} RMB")
            sum_c3.metric("$ 台幣總金額 (自動換算)", f"{total_twd:,.2f} TWD", f"目前匯率: {rate}")

            # 提交寫入資料庫邏輯（含成敗通知）
            if st.button("🚀 提交並儲存此採購單", type="primary", use_container_width=True):
                if not supplier_input.strip():
                    st.error("❌ 儲存失敗：採購廠商為必填項目，請勿留空！")
                elif edited_items.empty or total_qty == 0:
                    st.error("❌ 儲存失敗：採購單內必須包含至少一項商品且數量大於 0！")
                else:
                    try:
                        # 自動生成唯一採購單號 PO-YYYYMMDD-隨機流水碼
                        order_id = f"PO-{time.strftime('%Y%m%d')}-{int(time.time())%100000:05d}"
                        with get_db() as conn:
                            cursor = conn.cursor()
                            # 1. 寫入主表
                            cursor.execute("""
                                INSERT INTO procurement_orders (order_id, date, supplier, total_qty, total_amount_rmb, total_amount_twd, warehouse, staff, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '待驗收')
                            """, (order_id, str(date_input), supplier_input.strip(), total_qty, total_rmb, total_twd, warehouse_input, staff_input))
                            
                            # 2. 寫入明細細項
                            for _, row in edited_items.iterrows():
                                if str(row['商品編碼']).strip() and row['數量'] > 0:
                                    item_total_rmb = int(row['數量']) * float(row['人民幣單價'])
                                    cursor.execute("""
                                        INSERT INTO procurement_items (order_id, code, qty, unit_price_rmb, total_price_rmb)
                                        VALUES (?, ?, ?, ?, ?)
                                    """, (order_id, str(row['商品編碼']), int(row['數量']), float(row['人民幣單價']), item_total_rmb))
                            conn.commit()
                        st.success(f"✅ 採購單 【{order_id}】 建立並保存成功！請至核對頁面辦理點收。")
                        st.session_state.po_editor_df = pd.DataFrame(columns=["商品編碼", "數量", "人民幣單價"]) # 清空暫存
                        time.sleep(1.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ 資料庫寫入異常，單據儲存失敗！錯誤詳情：{str(e)}")

    # ==========================================
    # --- Tab 2: 採購單歷史與驗收入庫 (連結商品庫存) ---
    # ==========================================
    with tab2:
        st.subheader("📋 採購單據維護與點收庫存作業")
        with get_db() as conn:
            df_orders = pd.read_sql("""
                SELECT order_id as 採購單號, date as 日期, supplier as 廠商, 
                       total_qty as 總數量, total_amount_rmb as 人民幣總額, 
                       total_amount_twd as 台幣總額, warehouse as 購入倉庫, 
                       staff as 採購人員, status as 狀態 
                FROM procurement_orders ORDER BY 日期 DESC, order_id DESC
            """, conn)
            
        if df_orders.empty:
            st.info("目前系統中無任何採購歷史紀錄。")
        else:
            # 顯示主表清單
            st.dataframe(df_orders, use_container_width=True, hide_index=True)
            
            st.divider()
            # 點選單號打開詳細明細內容，並包含商品圖片
            selected_po = st.selectbox("🔍 請選取採購單號以展開「詳細明細內容」與辦理進貨點收入庫：", df_orders['採購單號'].tolist())
            
            if selected_po:
                order_meta = df_orders[df_orders['採購單號'] == selected_po].iloc[0]
                
                with get_db() as conn:
                    df_items = pd.read_sql("""
                        SELECT i.code as 編碼, p.名稱 as 名稱, p.圖片路徑, 
                               i.qty as 數量, i.unit_price_rmb as 單價, i.total_price_rmb as 總金額
                        FROM procurement_items i
                        LEFT JOIN products p ON i.code = p.編碼
                        WHERE i.order_id = ?
                    """, conn, params=(selected_po,))
                
                st.write(f"📁 **採購單號：** `{selected_po}` ｜ **狀態：** `{order_meta['狀態']}` ｜ **目的地倉庫：** `{order_meta['購入倉庫']}`")
                
                # 依需求排版顯示：編碼、名稱、圖片、數量、單價、總金額
                for _, item in df_items.iterrows():
                    with st.container(border=True):
                        img_c, details_c = st.columns([1.2, 6])
                        # 圖片欄位顯示
                        if item['圖片路徑'] and os.path.exists(item['圖片路徑']):
                            img_c.image(item['圖片路徑'], width=90)
                        else:
                            img_c.write("無商品圖片")
                        
                        details_c.markdown(
                            f"🆔 **商品編碼**：`{item['編碼']}`  &nbsp;&nbsp;&nbsp;&nbsp; 📦 **商品名稱**：**{item['名稱']}**\n\n"
                            f"🔢 **採購數量**：`{item['數量']}` 支 ｜ 💰 **人民幣單價**：`{item['單價']}` RMB ｜ 🧾 **項目總金額**：`{item['總金額']}` RMB"
                        )

                # 💡 進貨點收連結商品庫存功能
                if order_meta['狀態'] == '待驗收':
                    st.write("")
                    if st.button(f"🚚 點收完成！確認將單號 {selected_po} 的商品數量正式撥入『商品庫存』", type="primary", use_container_width=True):
                        try:
                            with get_db() as conn:
                                cursor = conn.cursor()
                                # 逐筆把採購明細的品項加進庫存流水表 inventory 中
                                for _, item in df_items.iterrows():
                                    cursor.execute("""
                                        INSERT INTO inventory (編碼, 倉庫位置, 數量, 單支成本_RMB, 採購廠商, 採購金額_RMB, 進貨日期)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """, (item['編碼'], order_meta['購入倉庫'], item['數量'], item['單價'], order_meta['廠商'], item['總金額'], order_meta['日期']))
                                
                                # 更新此張採購單的狀態改為『已入庫』，防止重複點收入庫
                                cursor.execute("UPDATE procurement_orders SET status = '已入庫' WHERE order_id = ?", (selected_po,))
                                conn.commit()
                            st.success(f"✅ 點收入庫成功！採購單 {selected_po} 已正式與庫存完成連動，數量已匯入庫存。")
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ 庫存撥配連動過程中發生異常錯誤：{str(e)}")
                else:
                    st.write("")
                    st.success("🎉 此採購單已完成點收入庫驗收，商品數量已在『商品庫存管理』核算中。")

    # ==========================================
    # --- Tab 3: 導入與導出功能 (Excel 處理) ---
    # ==========================================
    with tab3:
        st.subheader("📤 導出公司完整採購報表")
        try:
            with get_db() as conn:
                df_report = pd.read_sql("""
                    SELECT o.order_id as 採購單號, o.date as 日期, o.supplier as 廠商, 
                           o.warehouse as 購入倉庫, o.staff as 採購人員, o.status as 狀態,
                           i.code as 商品編碼, i.qty as 採購數量, i.unit_price_rmb as 人民幣單價, i.total_price_rmb as 人民幣總額
                    FROM procurement_orders o
                    JOIN procurement_items i ON o.order_id = i.order_id
                    ORDER BY o.date DESC, o.order_id DESC
                """, conn)
            
            from io import BytesIO
            output_excel = BytesIO()
            with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                df_report.to_excel(writer, index=False, sheet_name='採購明細總表')
            
            st.download_button(
                label="💾 點擊下載完整採購歷史明細報表 (Excel 格式)",
                data=output_excel.getvalue(),
                file_name="procurement_global_report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"❌ 報表導出模組發生例外錯誤：{str(e)}")

        st.divider()
        st.subheader("📥 導入外部採購單資料")
        st.caption("💡 批次匯入 Excel / CSV 欄位名稱順序必須包含：日期, 廠商, 購入倉庫, 採購人員, 商品編碼, 數量, 人民幣單價")
        
        uploaded_po = st.file_uploader("選擇您要上傳的批次採購檔案", type=["csv", "xlsx"])
        
        if uploaded_po and st.button("🚀 執行批量採購單據匯入作業", type="primary"):
            try:
                if uploaded_po.name.endswith('.csv'):
                    df_imp = pd.read_csv(uploaded_po)
                else:
                    df_imp = pd.read_excel(uploaded_po, engine='openpyxl')
                
                required_cols = ["日期", "廠商", "購入倉庫", "採購人員", "商品編碼", "數量", "人民幣單價"]
                
                if not all(c in df_imp.columns for c in required_cols):
                    st.error(f"❌ 匯入失敗：檔案內必填欄位不符，必須完整包含：{required_cols}")
                else:
                    # 將相同日期、相同廠商、相同倉庫的資料合併歸類為同一個採購單號
                    df_imp['Group_Key'] = df_imp['日期'].astype(str) + "_" + df_imp['廠商'].astype(str) + "_" + df_imp['購入倉庫'].astype(str)
                    
                    with get_db() as conn:
                        cursor = conn.cursor()
                        for g_key, group in df_imp.groupby('Group_Key'):
                            base_row = group.iloc[0]
                            # 生成專屬單號
                            order_id = f"PO-IMP-{time.strftime('%Y%m%d')}-{int(time.time())%100000:05d}"
                            time.sleep(0.02) # 避免生成碰撞
                            
                            g_qty = int(group['數量'].sum())
                            g_rmb = float((group['數量'] * group['人民幣單價']).sum())
                            g_twd = g_rmb * rate
                            
                            # A. 寫入主表
                            cursor.execute("""
                                INSERT INTO procurement_orders (order_id, date, supplier, total_qty, total_amount_rmb, total_amount_twd, warehouse, staff, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, '待驗收')
                            """, (order_id, str(base_row['日期']), str(base_row['廠商']), g_qty, g_rmb, g_twd, str(base_row['購入倉庫']), str(base_row['採購人員'])))
                            
                            # B. 寫入該單據底下所有明細細項
                            for _, row in group.iterrows():
                                item_rmb = int(row['數量']) * float(row['人民幣單價'])
                                cursor.execute("""
                                    INSERT INTO procurement_items (order_id, code, qty, unit_price_rmb, total_price_rmb)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (order_id, str(row['商品編碼']), int(row['數量']), float(row['人民幣單價']), item_rmb))
                        
                        conn.commit()
                    st.success("✅ 外部採購單據批次匯入作業成功完成！所有新單據預設為『待驗收』狀態。")
                    time.sleep(1.5)
                    st.rerun()
            except Exception as e:
                st.error(f"❌ 批量解析匯入失敗：格式不正確或資料有誤。詳情：{str(e)}")
elif menu == "訂單明細":
    st.title("🧾 客戶訂單明細")
    if check_perm(role, "訂單明細", "can_view"):
        t1, t2, t3 = st.tabs(["📄 訂單列表", "🚚 出貨與物流狀態", "🔙 退換貨處理"])
        with t1: st.info("匯入或手動建立客戶訂單，包含訂購人資訊與明細。")
        with t2: st.info("追蹤超商/宅配等物流交寄狀態，出貨後自動扣除『商品庫存』。")
        with t3: st.info("處理客訴退回，退回的商品可選擇是否重新加回庫存。")
    else: st.error("🚫 您無權限訪問此模組")

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
    
    if st.session_state.get('user') != 'admin' and role != "Admin": 
        st.error("🚫 僅限總管理員訪問此頁面")
        st.stop()
        
    st.info("💡 **操作說明**：\n"
            "1. **新增帳號**：滑到表格最底下，點擊空白列即可新增。\n"
            "2. **修改密碼**：直接將密碼刪除並輸入新密碼即可。\n"
            "3. **刪除帳號**：點選表格左側的核取方塊，按下鍵盤 `Delete` 鍵即可刪除該列。\n"
            "4. 修改完成後，請務必點擊下方的 **「儲存所有變更」** 按鈕。")
    
    modules = ["商品訊息", "商品庫存", "採購管理", "訂單明細", "財務報表"]
    
    with get_db() as conn:
        df_users = pd.read_sql("SELECT username, password, role FROM users", conn)
        
        # 🌟 讀取資料庫時，馬上把密碼解碼回明文，讓你在畫面上能直接看見！
        df_users['password'] = df_users['password'].apply(decode_pw)
        
        for m in modules:
            df_users[m] = df_users['role'].apply(lambda x: True if x == 'Admin' else (m in str(x)))
            
        df_display = df_users[['username', 'password'] + modules].copy()
        df_display.rename(columns={'username': '帳號', 'password': '密碼'}, inplace=True)
        
        edited_df = st.data_editor(
            df_display, 
            num_rows="dynamic", 
            use_container_width=True,
            column_config={
                "帳號": st.column_config.TextColumn("👤 帳號 (必填不可重複)"),
                "密碼": st.column_config.TextColumn("🔑 密碼 (此處顯示為明文)")
            }
        )
        
        if st.button("💾 確認儲存所有變更", type="primary", use_container_width=True):
            try:
                current_users = edited_df['帳號'].dropna().astype(str).tolist()
                current_users = [u.strip() for u in current_users if u.strip() != '']
                
                if not current_users:
                    st.error("❌ 系統至少需要保留一個帳號！")
                elif 'admin' not in current_users:
                    st.error("❌ 為了系統安全，禁止刪除預設的 'admin' 帳號！")
                else:
                    cursor = conn.cursor()
                    
                    placeholders = ','.join(['?'] * len(current_users))
                    cursor.execute(f"DELETE FROM users WHERE username NOT IN ({placeholders})", current_users)
                    
                    for _, row in edited_df.iterrows():
                        u_name = str(row['帳號']).strip()
                        u_pwd = str(row['密碼']).strip()
                        
                        if not u_name or u_name == 'nan': 
                            continue 
                        
                        # 🌟 寫回資料庫前，將你在畫面上看到的明文密碼再次隱藏編碼
                        u_pwd_encoded = encode_pw(u_pwd)
                            
                        assigned_modules = [m for m in modules if row[m] == True]
                        new_role_str = ",".join(assigned_modules)
                        
                        if u_name == 'admin':
                            new_role_str = 'Admin'
                            
                        cursor.execute("""
                            INSERT OR REPLACE INTO users (username, password, role) 
                            VALUES (?, ?, ?)
                        """, (u_name, u_pwd_encoded, new_role_str))
                        
                    conn.commit()
                    st.success("✅ 帳號與所有權限配置已成功更新！")
                    time.sleep(1.5)
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ 儲存失敗發生異常：{str(e)}")
