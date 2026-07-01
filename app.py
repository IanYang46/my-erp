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
def init_db_v2():
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
        
        # 🌟 【新增】4-1. 採購單主表
        cursor.execute('''CREATE TABLE IF NOT EXISTS purchase_orders (
                            採購單號 TEXT PRIMARY KEY,
                            日期 DATE,
                            廠商 TEXT,
                            總數量 INTEGER,
                            人民幣總金額 REAL,
                            台幣總金額 REAL,
                            購入倉庫 TEXT,
                            採購人員 TEXT,
                            狀態 TEXT DEFAULT '未入庫')''')
                            
        # 🌟 【新增】4-2. 採購單明細表
        cursor.execute('''CREATE TABLE IF NOT EXISTS purchase_items (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            採購單號 TEXT,
                            商品編碼 TEXT,
                            數量 INTEGER,
                            人民幣單價 REAL,
                            總金額_RMB REAL)''')
        
        # 4. 匯率設定表
        cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value REAL)''')
        cursor.execute("INSERT OR IGNORE INTO settings VALUES ('exchange_rate', 4.5)")
        
        # 5. 建立預設 Admin 帳號
        cursor.execute("INSERT OR IGNORE INTO users VALUES ('admin', ?, 'Admin')", (encode_pw('123456'),))
        
        # 6. 初始化全新權限矩陣
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
    st.title("🏭 商品庫存管理")

    with get_db() as conn:
        rate = conn.execute("SELECT value FROM settings WHERE key='exchange_rate'").fetchone()[0]
    
    new_rate = st.sidebar.number_input("當前人民幣匯率 (RMB to TWD)", value=rate, step=0.01)
    if st.sidebar.button("更新匯率"):
        with get_db() as conn:
            conn.execute("UPDATE settings SET value=? WHERE key='exchange_rate'", (new_rate,))
            conn.commit()
        st.rerun()

    if check_perm(role, "商品庫存", "can_view"):
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
        
        df["總庫存金額_RMB"] = df["總採購金額_RMB"]
        df["總庫存金額_TWD"] = df["總庫存金額_RMB"] * new_rate
        df["平均成本_TWD"] = df["平均成本_RMB"] * new_rate
        
        show_type = st.radio("篩選庫存狀態", ["顯示所有", "僅顯示有庫存", "僅顯示缺貨"], horizontal=True)
        filtered_df = df.copy()
        if show_type == "僅顯示有庫存": filtered_df = filtered_df[filtered_df["總庫存"] > 0]
        elif show_type == "僅顯示缺貨": filtered_df = filtered_df[filtered_df["總庫存"] <= 0]
        
        st.dataframe(filtered_df, use_container_width=True)
        
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
        st.error("🚫 您無權限訪問此模組")

elif menu == "採購管理":
    st.title("🛒 採購與進貨管理")
    
    # 取得當前系統預設匯率
    with get_db() as conn:
        po_rate = conn.execute("SELECT value FROM settings WHERE key='exchange_rate'").fetchone()[0]
        
    if check_perm(role, "採購管理", "can_view"):
        
        # 初始化編輯狀態監聽
        if 'edit_po_id' not in st.session_state:
            st.session_state['edit_po_id'] = None
            
        # ------------------ 模式切換：獨立編輯畫面 ------------------
        if st.session_state['edit_po_id'] is not None:
            target_po = st.session_state['edit_po_id']
            st.subheader(f"✏️ 修正/編輯採購單：{target_po}")
            
            if st.button("🔙 取消並返回採購清單"):
                st.session_state['edit_po_id'] = None
                st.rerun()
                
            with get_db() as conn:
                po_master = pd.read_sql("SELECT * FROM purchase_orders WHERE 採購單號=?", conn, params=(target_po,)).iloc[0]
                po_items = pd.read_sql("SELECT 商品編碼, 數量, 人民幣單價 FROM purchase_items WHERE 採購單號=?", conn, params=(target_po,))
                df_prod_list = pd.read_sql("SELECT 編碼 FROM products ORDER BY 編碼 ASC", conn)
                all_prods = df_prod_list['編碼'].tolist()
                
            with st.form("edit_po_form"):
                c1, c2, c3, c4 = st.columns(4)
                e_date = c1.date_input("採購日期", value=pd.to_datetime(po_master['日期']))
                e_supplier = c2.text_input("供應商", value=po_master['廠商'])
                e_wh = c3.text_input("購入倉庫", value=po_master['購入倉庫'])
                e_user = c4.text_input("採購人員", value=po_master['採購人員'])
                
                st.write("📦 修正採購商品項目 (可自行增減列)：")
                edited_items_df = st.data_editor(
                    po_items, num_rows="dynamic", use_container_width=True, key="po_item_editor",
                    column_config={
                        "商品編碼": st.column_config.SelectboxColumn("商品編碼", options=all_prods, required=True),
                        "數量": st.column_config.NumberColumn("數量", min_value=1, step=1, default=1),
                        "人民幣單價": st.column_config.NumberColumn("人民幣單價 (RMB)", min_value=0.0, step=0.01)
                    }
                )
                
                if st.form_submit_button("💾 儲存採購單修改", type="primary"):
                    try:
                        valid_items = edited_items_df.dropna(subset=['商品編碼']).copy()
                        if valid_items.empty:
                            st.error("❌ 採購單不能沒有任何商品項目！")
                        else:
                            valid_items['總金額_RMB'] = valid_items['數量'] * valid_items['人民幣單價']
                            total_qty = int(valid_items['數量'].sum())
                            total_rmb = float(valid_items['總金額_RMB'].sum())
                            total_twd = round(total_rmb * po_rate, 2)
                            
                            with get_db() as conn:
                                cursor = conn.cursor()
                                # 更新主表
                                cursor.execute("""
                                    UPDATE purchase_orders 
                                    SET 日期=?, 廠商=?, 總數量=?, 人民幣總金額=?, 台幣總金額=?, 購入倉庫=?, 採購人員=?
                                    WHERE 採購單號=?
                                """, (str(e_date), e_supplier, total_qty, total_rmb, total_twd, e_wh, e_user, target_po))
                                
                                # 重新整理明細表 (先刪再蓋)
                                cursor.execute("DELETE FROM purchase_items WHERE 採購單號=?", (target_po,))
                                for _, row in valid_items.iterrows():
                                    cursor.execute("""
                                        INSERT INTO purchase_items (採購單號, 商品編碼, 數量, 人民幣單價, 總金額_RMB)
                                        VALUES (?, ?, ?, ?, ?)
                                    """, (target_po, str(row['商品編碼']), int(row['數量']), float(row['人民幣單價']), float(row['總金額_RMB'])))
                                conn.commit()
                            st.success(f"✅ 採購單 {target_po} 已成功修正更新！")
                            st.session_state['edit_po_id'] = None
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ 修改失敗，發生異常：{str(e)}")
                        
        # ------------------ 正常模組畫面 (分頁籤) ------------------
        else:
            tab1, tab2, tab3 = st.tabs(["📋 採購單瀏覽與入庫驗收", "➕ 新增採購訂單", "📥 批次匯入/匯出"])
            
            # --- Tab 1: 瀏覽與核對明細 ---
            with tab1:
                with get_db() as conn:
                    df_po = pd.read_sql("SELECT * FROM purchase_orders ORDER BY 日期 DESC", conn)
                    
                if df_po.empty:
                    st.info("目前尚無任何採購單紀錄。")
                else:
                    selected_po = st.selectbox("🔍 選擇要檢視詳細內容或操作的採購單：", ["請選擇採購單..."] + df_po['採購單號'].tolist())
                    
                    if selected_po != "請選擇採購單...":
                        po_info = df_po[df_po['採購單號'] == selected_po].iloc[0]
                        
                        # 看板式摘要資訊
                        with st.container(border=True):
                            st.subheader(f"📄 採購單基本資料 ({po_info['採購單號']})")
                            m_c1, m_c2, m_c3, m_c4 = st.columns(4)
                            m_c1.write(f"📅 **採購日期**：{po_info['日期']}")
                            m_c2.write(f"🏭 **供應廠商**：{po_info['廠商']}")
                            m_c3.write(f"🛒 **採購人員**：{po_info['採購人員']}")
                            m_c4.write(f"🏢 **購入倉庫**：{po_info['購入倉庫']}")
                            
                            m_c1.write(f"📊 **總數量**：{po_info['總數量']} 支")
                            m_c2.write(f"💰 **人民幣總額**：¥{po_info['人民幣總金額']:.2f}")
                            m_c3.write(f"💵 **台幣估算總額**：NT${po_info['台幣總金額']:.2f}")
                            
                            status_color = "🟢" if po_info['狀態'] == '已入庫' else "🟡"
                            m_c4.write(f"{status_color} **目前的狀態**：{po_info['狀態']}")
                        
                        # 顯示商品詳細內容表 (包含圖片、名稱)
                        st.write("📋 **採購商品詳細清單：**")
                        with get_db() as conn:
                            df_items = pd.read_sql("""
                                SELECT i.*, p.名稱, p.圖片路徑 
                                FROM purchase_items i
                                LEFT JOIN products p ON i.商品編碼 = p.編碼
                                WHERE i.採購單號 = ?
                            """, conn, params=(selected_po,))
                            
                        for _, item in df_items.iterrows():
                            with st.container(border=True):
                                col_img, col_info, col_qty, col_price, col_tot = st.columns([1.5, 4, 1.5, 2, 2])
                                # 1. 圖片
                                if item['圖片路徑'] and os.path.exists(item['圖片路徑']):
                                    col_img.image(item['圖片路徑'], width=70)
                                else:
                                    col_img.write("無圖")
                                # 2. 商品訊息
                                col_info.write(f"**編碼**: {item['商品編碼']}")
                                col_info.write(f"**名稱**: {item['名稱'] if item['名稱'] else '---'}")
                                # 3. 數量與單價
                                col_qty.write(f"**數量**\n### {item['數量']}")
                                col_price.write(f"**人民幣單價**\n¥ {item['人民幣單價']:.2f}")
                                col_tot.write(f"**小計金額**\n¥ {item['總金額_RMB']:.2f}\n(NT${round(item['總金額_RMB']*po_rate, 1)})")
                        
                        st.divider()
                        # 操作功能列
                        act_c1, act_c2, act_c3 = st.columns(3)
                        
                        # A. 入庫動作
                        if po_info['狀態'] == '未入庫':
                            if act_c1.button("🚚 執行驗收，確認點收入庫", type="primary", use_container_width=True):
                                try:
                                    with get_db() as conn:
                                        cursor = conn.cursor()
                                        # 將採購項目全數倒入庫存表 inventory
                                        for _, item in df_items.iterrows():
                                            cursor.execute("""
                                                INSERT INTO inventory (編碼, 倉庫位置, 數量, 單支成本_RMB, 採購廠商, 採購金額_RMB, 進貨日期)
                                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                            """, (item['商品編碼'], po_info['購入倉庫'], item['數量'], item['人民幣單價'], po_info['廠商'], item['總金額_RMB'], po_info['日期']))
                                        # 更新本單狀態
                                        cursor.execute("UPDATE purchase_orders SET 狀態='已入庫' WHERE 採購單號=?", (selected_po,))
                                        conn.commit()
                                    st.success(f"🎉 採購單 {selected_po} 驗收完成！商品數量已全數加進『商品庫存』。")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ 入庫作業失敗：{str(e)}")
                        else:
                            act_c1.button("✅ 此單已完成驗收入庫", disabled=True, use_container_width=True)
                            
                        # B. 編輯單據
                        if act_c2.button("✏️ 編輯修改此單內容", use_container_width=True):
                            if po_info['狀態'] == '已入庫':
                                st.warning("⚠️ 此採購單已執行過入庫，直接修改明細可能導致與目前庫存數量不符，請謹慎操作。")
                            st.session_state['edit_po_id'] = selected_po
                            st.rerun()
                            
                        # C. 刪除單據
                        if act_c3.button("🗑️ 刪除此筆採購訂單", type="primary", use_container_width=True):
                            try:
                                with get_db() as conn:
                                    cursor = conn.cursor()
                                    cursor.execute("DELETE FROM purchase_orders WHERE 採購單號=?", (selected_po,))
                                    cursor.execute("DELETE FROM purchase_items WHERE 採購單號=?", (selected_po,))
                                    conn.commit()
                                st.success(f"🗑️ 採購單 {selected_po} 及相關明細已徹底刪除。")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ 刪除採購單失敗：{str(e)}")
                                
            # --- Tab 2: 手動新增採購單 ---
            with tab2:
                st.subheader("➕ 建立新採購單項目")
                # 自動產生一個不易重複的單號
                suggested_id = f"PO-{time.strftime('%Y%m%d-%H%M%S')}"
                
                with get_db() as conn:
                    df_prod_list = pd.read_sql("SELECT 編碼 FROM products ORDER BY 編碼 ASC", conn)
                    all_prods = df_prod_list['編碼'].tolist()
                    
                if not all_prods:
                    st.warning("⚠️ 商品訊息庫目前沒有任何商品，請先至『商品訊息』模組建立商品才能進行採購。")
                else:
                    with st.form("add_po_form", clear_on_submit=True):
                        col_x1, col_x2 = st.columns(2)
                        new_po_id = col_x1.text_input("採購單號 (可留空用系統自動產生)", value=suggested_id)
                        new_po_date = col_x2.date_input("採購日期")
                        
                        col_x3, col_x4, col_x5 = st.columns(3)
                        new_po_supplier = col_x3.text_input("供應商名稱")
                        new_po_wh = col_x4.text_input("預計購入倉庫位置 (如：A倉、高雄倉)", value="主倉庫")
                        new_po_user = col_x5.text_input("採購經辦人員", value=st.session_state.get('user', ''))
                        
                        st.write("📝 請於下方建立商品項目與採購單價：")
                        # 預設乾淨的一列資料供填寫
                        init_df = pd.DataFrame([{"商品編碼": all_prods[0], "數量": 1, "人民幣單價": 0.0}])
                        
                        new_items_df = st.data_editor(
                            init_df, num_rows="dynamic", use_container_width=True, key="new_po_editor",
                            column_config={
                                "商品編碼": st.column_config.SelectboxColumn("商品編碼", options=all_prods, required=True),
                                "數量": st.column_config.NumberColumn("數量", min_value=1, step=1, default=1),
                                "人民幣單價": st.column_config.NumberColumn("人民幣單價 (RMB)", min_value=0.0, step=0.01)
                            }
                        )
                        
                        if st.form_submit_button("🚀 確認建立並儲存此採購單", type="primary"):
                            try:
                                valid_new_items = new_items_df.dropna(subset=['商品編碼']).copy()
                                if valid_new_items.empty:
                                    st.error("❌ 建立失敗：採購清單內不可為空！")
                                else:
                                    # 計算金額與總量
                                    valid_new_items['總金額_RMB'] = valid_new_items['數量'] * valid_new_items['人民幣單價']
                                    total_qty = int(valid_new_items['數量'].sum())
                                    total_rmb = float(valid_new_items['總金額_RMB'].sum())
                                    total_twd = round(total_rmb * po_rate, 2)
                                    final_po_id = new_po_id.strip() if new_po_id.strip() else suggested_id
                                    
                                    with get_db() as conn:
                                        cursor = conn.cursor()
                                        # 寫入主表
                                        cursor.execute("""
                                            INSERT INTO purchase_orders (採購單號, 日期, 廠商, 總數量, 人民幣總金額, 台幣總金額, 購入倉庫, 採購人員, 狀態)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, '未入庫')
                                        """, (final_po_id, str(new_po_date), new_po_supplier, total_qty, total_rmb, total_twd, new_po_wh, new_po_user))
                                        
                                        # 寫入明細
                                        for _, row in valid_new_items.iterrows():
                                            cursor.execute("""
                                                INSERT INTO purchase_items (採購單號, 商品編碼, 數量, 人民幣單價, 總金額_RMB)
                                                VALUES (?, ?, ?, ?, ?)
                                            """, (final_po_id, str(row['商品編碼']), int(row['數量']), float(row['人民幣單價']), float(row['總金額_RMB'])))
                                        conn.commit()
                                    st.success(f"🎉 採購單 {final_po_id} 建立成功！狀態目前為「未入庫」，請至清單分頁執行驗收。")
                                    time.sleep(1)
                                    st.rerun()
                            except sqlite3.IntegrityError:
                                st.error(f"❌ 建立失敗：採購單號【{new_po_id}】已存在，請使用其他單號。")
                            except Exception as e:
                                st.error(f"❌ 建立單據失敗：{str(e)}")
                                
            # --- Tab 3: 批次作業與導出 ---
            with tab3:
                st.subheader("📤 下載所有採購單歷史報表")
                if df_po.empty:
                    st.caption("暫無歷史資料可供導出。")
                else:
                    from io import BytesIO
                    output_po = BytesIO()
                    with pd.ExcelWriter(output_po, engine='openpyxl') as writer:
                        df_po.to_excel(writer, index=False, sheet_name='採購單總表')
                    
                    st.download_button(
                        label="💾 導出採購單主表 (Excel)",
                        data=output_po.getvalue(),
                        file_name="purchase_orders_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                st.divider()
                st.subheader("📥 批量匯入採購單 (開發預留區塊)")
                st.info("此區塊未來可配合物流格式直接上傳廠商 CSV 檔批量產單。目前建議使用【新增採購訂單】分頁進行動態極速建立。")
    else:
        st.error("🚫 您無權限訪問此模組")

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
