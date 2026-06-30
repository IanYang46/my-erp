import streamlit as st
import sqlite3
import pandas as pd
import os
import time

# --- 1. 基礎設定與整地 ---
if not os.path.exists("product_images"): os.makedirs("product_images")
st.set_page_config(page_title="強盛集團 ERP", layout="wide", initial_sidebar_state="expanded")

# --- 2. 穩定的資料庫連線 ---
def get_db():
    # 這是你的雲端資料庫網址 (建議將密碼替換為你實際設定的密碼)
    DATABASE_URL = "postgresql://postgres:cihhib-wuvjog-0gaQfu@db.qmrqwmvboetgdthwgesw.supabase.co:5432/postgres"

    # 判斷是否在雲端環境執行 (Render 會自動設定環境變數)
    if os.environ.get("RENDER"):
        return create_engine(DATABASE_URL).connect()
    else:
        # 如果是本地端，還是用你原本的 SQLite 檔案，方便你測試
        import sqlite3
        return sqlite3.connect("powerful_group.db")

# --- 3. 初始化資料庫與預設權限 ---
def init_db():
    # 從 st.secrets 讀取帳號密碼
    admin_user = st.secrets.get("ADMIN_USERNAME", "admin")
    admin_pw = st.secrets.get("ADMIN_PASSWORD", "123456")
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. 建立系統核心表格
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS permissions (role TEXT, module TEXT, can_view BOOLEAN, can_edit BOOLEAN, can_upload BOOLEAN, can_download BOOLEAN)''')
        
        # 2. 商品資料表 (已包含類別、品牌等 6 個欄位)
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (
                            編碼 TEXT PRIMARY KEY, 
                            類別 TEXT, 
                            品牌 TEXT, 
                            名稱 TEXT, 
                            備註 TEXT, 
                            圖片路徑 TEXT)''')
        
        # 3. 【新增】：庫存管理表
        cursor.execute('''CREATE TABLE IF NOT EXISTS inventory (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            編碼 TEXT,
                            倉庫位置 TEXT,
                            數量 INTEGER,
                            單支成本_RMB REAL,
                            採購廠商 TEXT,
                            採購金額_RMB REAL,
                            進貨日期 DATE)''')
        
        # 4. 【新增】：匯率設定表
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL)''')
        cursor.execute("INSERT OR IGNORE INTO settings VALUES ('exchange_rate', 4.5)")
        
        # 5. 建立預設 Admin 帳號
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, 'Admin')", (admin_user, admin_pw))
        
        # 6. 初始化全新權限矩陣 (對應您新增的模組)
        cursor.execute("SELECT count(*) FROM permissions")
        if cursor.fetchone()[0] == 0:
            modules = ["商品訊息", "商品庫存", "採購管理", "訂單明細", "財務報表"]
            roles = ["Admin", "Finance", "Shareholder", "CS"]
            for r in roles:
                v, e, u, d = (1, 1, 1, 1) if r == "Admin" else (0, 0, 0, 0)
                for m in modules:
                    cursor.execute("INSERT INTO permissions VALUES (?,?,?,?,?,?)", (r, m, v, e, u, d))
        
        conn.commit()
init_db()

# --- 4. 權限檢查工具 ---
def check_perm(role, module, action):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT {action} FROM permissions WHERE role=? AND module=?", (role, module))
        res = cursor.fetchone()
        return bool(res[0]) if res else False

# --- 5. 系統登入 ---
if 'logged_in' not in st.session_state:
    st.title("📦 強盛集團 | ERP 系統登入")
    with st.form("login_form"):
        user = st.text_input("帳號")
        pw = st.text_input("密碼", type="password")
        if st.form_submit_button("登入"):
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT role FROM users WHERE username=? AND password=?", (user, pw))
                res = cursor.fetchone()
                if res:
                    st.session_state.update({'logged_in': True, 'role': res[0], 'user': user})
                    st.rerun()
                else:
                    st.error("帳號或密碼錯誤！")
    st.stop()

# --- 6. 側邊欄設計 ---
st.sidebar.title("🏢 強盛集團 ERP")
st.sidebar.info(f"👤 帳號: {st.session_state['user']} \n🔑 角色: {st.session_state['role']}")
if st.sidebar.button("登出系統", use_container_width=True): 
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()

# 定義選單 (加入 key 避免快取消失)
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
        
        # --- 1. 列表瀏覽與獨立編輯頁面 ---
        with tab1:
            if 'edit_item_code' not in st.session_state:
                st.session_state['edit_item_code'] = None
                
            if st.session_state['edit_item_code'] is None:
                # 畫面 A：顯示商品列表
                with get_db() as conn:
                    # 🌟 關鍵修改：加入 ORDER BY 編碼 ASC 讓列表自動按編碼排序
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
                # 畫面 B：獨立編輯介面
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
                
        # --- 2. 新增商品 ---
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

        # --- 3. 批次作業 ---
        with tab3:
            st.subheader("📥 批量下載完整商品表")
            if check_perm(role, "商品訊息", "can_download"):
                with get_db() as conn:
                    df_all = pd.read_sql("SELECT 編碼, 類別, 品牌, 名稱, 備註 FROM products ORDER BY 編碼 ASC", conn)
                
                # 修正後的 Excel 匯出邏輯
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
                # 這裡的邏輯原本就是對的，保持不動即可
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
    st.title("🏭 商品庫存管理")

    # 取得最新匯率
    with get_db() as conn:
        rate = conn.execute("SELECT value FROM settings WHERE key='exchange_rate'").fetchone()[0]
    
    # 匯率手動調整
    new_rate = st.sidebar.number_input("當前人民幣匯率 (RMB to TWD)", value=rate, step=0.01)
    if st.sidebar.button("更新匯率"):
        with get_db() as conn:
            conn.execute("UPDATE settings SET value=? WHERE key='exchange_rate'", (new_rate,))
            conn.commit()
        st.rerun()

    if check_perm(role, "商品庫存", "can_view"):
        # 1. 讀取數據並計算
        with get_db() as conn:
            query = """
            SELECT p.編碼, p.名稱, p.類別, p.品牌, 
                   IFNULL(SUM(i.數量), 0) as 總庫存,
                   IFNULL(SUM(i.採購金額_RMB), 0) as 總採購金額_RMB,
                   AVG(i.單支成本_RMB) as 平均成本_RMB
            FROM products p
            LEFT JOIN inventory i ON p.編碼 = i.編碼
            GROUP BY p.編碼
            """
            df = pd.read_sql(query, conn)
        
        # 2. 計算欄位
        df["總庫存金額_RMB"] = df["總採購金額_RMB"]
        df["總庫存金額_TWD"] = df["總庫存金額_RMB"] * new_rate
        df["平均成本_TWD"] = df["平均成本_RMB"] * new_rate
        
        # 3. 篩選與顯示
        show_type = st.radio("篩選庫存狀態", ["顯示所有", "僅顯示有庫存", "僅顯示缺貨"], horizontal=True)
        filtered_df = df.copy()
        if show_type == "僅顯示有庫存": filtered_df = filtered_df[filtered_df["總庫存"] > 0]
        elif show_type == "僅顯示缺貨": filtered_df = filtered_df[filtered_df["總庫存"] <= 0]
        
        st.dataframe(filtered_df, use_container_width=True)
        
        # 4. 新增：批量下載功能
        from io import BytesIO
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            filtered_df.to_excel(writer, index=False, sheet_name='Inventory')
        
        st.download_button(
            label="💾 下載庫存報表 (Excel)",
            data=output.getvalue(),
            file_name="inventory_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # 5. 批次進貨 (匯入)
        with st.expander("📥 批次進貨匯入 (Excel/CSV)"):
            st.write("請上傳包含：編碼, 倉庫位置, 數量, 單支成本_RMB, 採購廠商, 進貨日期 的檔案")
            uploaded_file = st.file_uploader("上傳進貨單", type=["csv", "xlsx"])
            if uploaded_file and st.button("確認匯入進貨"):
                try:
                    df_in = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
                    with get_db() as conn:
                        df_in.to_sql('inventory', conn, if_exists='append', index=False)
                    st.success("進貨紀錄已更新！")
                    st.rerun()
                except Exception as e:
                    st.error(f"匯入錯誤: {e}")
    else:
        st.error("無權限查看")

elif menu == "採購管理":
    st.title("🛒 採購與進貨管理")
    if check_perm(role, "採購管理", "can_view"):
        t1, t2 = st.tabs(["📝 新增採購單", "🚚 進貨驗收入庫"])
        with t1: st.info("建立採購單，記錄供應商、預計成本與預計到貨日。")
        with t2: st.info("到貨時進行點收，點收後數量自動加進『商品庫存』。")
    else: st.error("🚫 您無權限訪問此模組")

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
    st.title("🔐 系統權限矩陣")
    if role != "Admin": 
        st.error("🚫 僅限總管理員訪問此頁面")
        st.stop()
    
    st.write("請直接勾選下方表格來開關各角色的模組權限：")
    with get_db() as conn:
        df_perm = pd.read_sql("SELECT * FROM permissions", conn)
        edited_perm = st.data_editor(df_perm, hide_index=True, use_container_width=True)
        if st.button("💾 儲存權限設定", type="primary"):
            edited_perm.to_sql('permissions', conn, if_exists='replace', index=False)
            st.success("✅ 權限已成功更新！")
            st.rerun()
