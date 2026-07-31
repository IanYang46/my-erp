import os
import time
import requests
import psycopg2
from psycopg2 import pool
import re

# 讀取環境變數
DB_URL = os.getenv("DB_URL")
ONESHOP_APP_ID = os.getenv("ONESHOP_APP_ID")
ONESHOP_SECRET = os.getenv("ONESHOP_SECRET")

# 建立獨立的連線池
db_pool = pool.ThreadedConnectionPool(1, 5, DB_URL, keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5)

def get_db_connection():
    return db_pool.getconn()

def release_db_connection(conn):
    db_pool.putconn(conn)

def sync_1shop_orders():
    print("🤖 開始執行 1shop 訂單自動同步作業...")
    if not ONESHOP_APP_ID or not ONESHOP_SECRET:
        print("❌ 錯誤：找不到 1shop 金鑰設定！")
        return

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. 取得當前匯率
        cursor.execute("SELECT value FROM settings WHERE key='exchange_rate'")
        rate_row = cursor.fetchone()
        rate = rate_row[0] if rate_row else 4.5

        # 2. 準備動態成本計算引擎所需的資料庫快取
        cursor.execute("SELECT 編碼, AVG(單支成本_RMB) FROM inventory GROUP BY 編碼")
        df_costs = cursor.fetchall()
        code_cost_map = {str(row[0]): float(row[1]) for row in df_costs}
        all_codes = sorted([str(c) for c in code_cost_map.keys() if str(c)], key=len, reverse=True)

        def calculate_dynamic_rmb_cost(items_string):
            if not items_string: return 50.0
            parts = re.split(r'[\n、,，]', str(items_string).replace('•', ''))
            total_rmb = 0.0
            has_match = False
            for part in parts:
                part = part.strip()
                if not part: continue
                match = re.search(r'[\*xX×]\s*(\d+)', part)
                qty = int(match.group(1)) if match else 1
                
                item_rmb = 50.0
                matched = False
                for code in all_codes:
                    if code in part:
                        item_rmb = code_cost_map.get(code, 50.0)
                        matched = True; break
                
                if matched: has_match = True
                total_rmb += (item_rmb * qty)
                
            if not has_match and total_rmb == 0:
                qty_sum = sum([int(re.search(r'[\*xX×]\s*(\d+)', p).group(1)) if re.search(r'[\*xX×]\s*(\d+)', p) else 1 for p in parts if p.strip()])
                total_rmb = (qty_sum if qty_sum > 0 else 1) * 50.0
            return total_rmb

        # 3. 呼叫 1shop API 取得訂單列表
        base_url = "https://api.1shop.tw/v1/order" 
        params = {
            "appid": ONESHOP_APP_ID,
            "secret": ONESHOP_SECRET,
            "progress_status": "all",
            "payment_status": "all",
            "logistic_status": "all"
        }
        
        print("📥 正在取得訂單列表...")
        response = requests.get(base_url, params=params, timeout=10)
        if response.status_code != 200:
            print(f"❌ 取得訂單列表失敗，狀態碼：{response.status_code}")
            return
            
        data = response.json()
        if data.get("success") != 0:
            print(f"❌ API 回傳錯誤：{data.get('msg')}")
            return
            
        orders_list = data.get("data", {}).get("order", [])
        if not orders_list:
            print("💡 目前沒有新的訂單。")
            return
            
        success_count = 0
        for basic_order in orders_list:
            oid = str(basic_order.get("order_number", "")).strip()
            if not oid: continue
            
            odate = str(basic_order.get("create_date", ""))
            name = str(basic_order.get("name", ""))
            phone = str(basic_order.get("phone", ""))
            email = str(basic_order.get("email", ""))
            store = str(basic_order.get("cvs_store_name", ""))
            store_id = str(basic_order.get("cvs_store_id", ""))
            rev = float(basic_order.get("total_price", 0.0))
            c_note = str(basic_order.get("note", ""))
            m_note = str(basic_order.get("shop_note", ""))
            
            raw_logistic_status = str(basic_order.get("logistic_status", "pending"))
            raw_progress_status = str(basic_order.get("progress_status", ""))
            
            status_mapping = {
                "pending": "待出貨", "prepare": "備貨中", "send": "配送中",
                "shipped": "配送中", "delivered": "已送達待取", "received": "簽收",
                "abnormal": "客訴", "returning": "退回", "delay": "待出貨", "returned": "退回"
            }
            if raw_progress_status in ["cancelled", "other"]:
                init_status = "已取消"
            else:
                init_status = status_mapping.get(raw_logistic_status, "待出貨")
            
            detail_url = f"https://api.1shop.tw/v1/order/{oid}"
            
            # 🌟 絕對關鍵：自動對抗 10秒10次限制 的減速防呆
            time.sleep(1.2) 
            
            detail_response = requests.get(detail_url, params={"appid": ONESHOP_APP_ID, "secret": ONESHOP_SECRET}, timeout=10)
            items_str = "未抓取到品項"
            item_count = 0
            o_url = ""
            
            if detail_response.status_code == 200:
                detail_data = detail_response.json()
                if detail_data.get("success") == 0:
                    detail_order_info = detail_data.get("data", {}).get("order", {})
                    o_url = str(detail_order_info.get("order_url", ""))
                    products = detail_data.get("data", {}).get("cart", {}).get("products") or []
                    item_lines = []
                    
                    for p in products:
                        p_type = p.get("product_type", "single")
                        if p_type == "charge": continue
                            
                        # 嚴格抓取 SKU 與數量
                        if p_type == "bundle":
                            bundle_contents = p.get("bundle", [])
                            bundle_qty = int(p.get("quantity", 1)) 
                            if isinstance(bundle_contents, list) and len(bundle_contents) > 0:
                                for b_item in bundle_contents:
                                    b_sku = str(b_item.get("sku", "")).strip()
                                    b_item_qty = int(b_item.get("quantity", 1)) * bundle_qty 
                                    item_lines.append(f"• {b_sku} *{b_item_qty}")
                                    item_count += b_item_qty
                            else:
                                p_sku = str(p.get("sku", "")).strip()
                                item_lines.append(f"• {p_sku} *{bundle_qty}")
                                item_count += bundle_qty
                        else:
                            p_sku = str(p.get("sku", "")).strip()
                            qty = int(p.get("quantity", 1))
                            item_lines.append(f"• {p_sku} *{qty}")
                            item_count += qty

                    if item_lines:
                        items_str = "\n".join(item_lines)
                    else:
                        items_str = f"系統解析異常，原始資料: {str(products)}"
            elif detail_response.status_code == 429:
                items_str = "⚠️ 抓取失敗：請求過快被 1shop 阻擋 (429)"
            else:
                items_str = f"⚠️ 抓取異常 (狀態碼: {detail_response.status_code})"
            
            if item_count == 0: item_count = 1
            
            dynamic_cost_rmb = calculate_dynamic_rmb_cost(items_str)
            default_cost_twd = dynamic_cost_rmb * rate
            init_profit = rev - default_cost_twd

            # 注意：此處必須使用 %s 作為佔位符 (純 psycopg2 語法)
            cursor.execute("""
                INSERT INTO customer_orders 
                (訂單編號, 訂單日期, 姓名, 電話, 信箱, 訂單連結, 門市, 店號, 品項內容, 下單總數, 包裹應收, 商品成本, 物流運費, 出貨成本, 訂單損益, 物流編號, 取貨狀態, 顧客備註, 商家備註)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0.0, %s, %s, '', %s, %s, %s)
                ON CONFLICT(訂單編號) DO UPDATE SET
                    姓名 = EXCLUDED.姓名,
                    電話 = EXCLUDED.電話,
                    信箱 = EXCLUDED.信箱,
                    訂單連結 = EXCLUDED.訂單連結,
                    門市 = EXCLUDED.門市,
                    店號 = EXCLUDED.店號,
                    品項內容 = EXCLUDED.品項內容,
                    下單總數 = EXCLUDED.下單總數,
                    包裹應收 = EXCLUDED.包裹應收,
                    商品成本 = EXCLUDED.商品成本,
                    出貨成本 = EXCLUDED.出貨成本,
                    訂單損益 = EXCLUDED.訂單損益,
                    取貨狀態 = CASE WHEN EXCLUDED.取貨狀態 = '已取消' THEN '已取消' ELSE EXCLUDED.取貨狀態 END,
                    顧客備註 = EXCLUDED.顧客備註,
                    商家備註 = EXCLUDED.商家備註;
            """, (
                oid, odate, name, phone, email, o_url, store, store_id, items_str, item_count, rev,
                default_cost_twd, default_cost_twd, init_profit, init_status, c_note, m_note
            ))
            success_count += 1
            print(f"✅ 成功處理/更新訂單: {oid}")

        # 寫入系統日誌
        if success_count > 0:
            cursor.execute("INSERT INTO system_logs (timestamp, module, operator, action_type, details) VALUES (%s, %s, %s, %s, %s)", 
                           (time.strftime('%Y-%m-%d %H:%M:%S'), "系統排程", "機器人", "自動背景同步", f"排程自動同步了 {success_count} 筆訂單"))
        conn.commit()
        print(f"🎉 同步完成！本次共處理 {success_count} 筆訂單。")
        
    except Exception as e:
        print(f"💥 執行過程中發生錯誤: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        release_db_connection(conn)

if __name__ == "__main__":
    print("🤖 啟動 1shop 背景自動同步服務...")
    
    while True:
        try:
            print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] 開始執行同步作業...")
            
            # 呼叫你上面寫好的同步函式
            sync_1shop_orders()
            
            print("✅ 該次回合執行完畢！")
        except Exception as e:
            # 如果發生預期外的嚴重錯誤，印出錯誤但「不要」讓程式崩潰停止
            print(f"❌ 嚴重錯誤: {e}")
        
        print("⏳ 進入休眠，等待 30 分鐘後再次抓取...\n")
        time.sleep(1800)  # 1800 秒 = 30 分鐘
