import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# 設定網頁標題與排版 (手機睇會自動適應寬度)
st.set_page_config(page_title="Stacking Tracker", layout="centered")

st.title("⏱️ Stacking Tracker")
st.markdown("快速記錄你的疊杯成績，挑戰 PB！")

# 1. 建立 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. 讀取數據 - 指定你的分頁名稱為 "Data"
try:
    # 呢度改咗做 worksheet="Data"
    df = conn.read(worksheet="Data")
    
    # 清理之前加落去保護字元的單引號 (如果有的話)
    if "Mode" in df.columns:
        df["Mode"] = df["Mode"].astype(str).str.lstrip("'")
        
    # 強制將 Time 轉做數字，方便計 PB
    df["Time"] = pd.to_numeric(df["Time"], errors='coerce')
except Exception as e:
    st.error(f"讀取失敗（請檢查 Sheet 名稱是否為 Data）：{e}")
    df = pd.DataFrame(columns=["Timestamp", "Name", "Mode", "Time"])

# 3. 讀取選手名單 - 嘗試指定分頁 "Players"，否則從 Data 中抽取或使用預設
try:
    players_df = conn.read(worksheet="Players")
    # 假設選手名單在第一欄
    if "Name" in players_df.columns:
        names = players_df["Name"].dropna().astype(str).tolist()
    else:
        # Google Sheets 讀取時，預設會將第一行當作標題。
        # 如果沒有特別寫 "Name" 做標題，第一個名字 (例如 Johnny) 就會變咗做欄位名稱 (Column Name)。
        col_name = str(players_df.columns[0])
        names = []
        # 如果第一個名唔係類似 "Unnamed: 0" 嘅無效名稱，就加返入名單度
        if not col_name.startswith("Unnamed"):
            names.append(col_name)
        # 加返其餘嘅名字
        names.extend(players_df.iloc[:, 0].dropna().astype(str).tolist())
    # 過濾空白名稱
    names = [n.strip() for n in names if n.strip()]
except Exception:
    # 如果沒有 Players 分頁，就從 Data 的紀錄入面攞 unique 名字，再加個預設
    if not df.empty and "Name" in df.columns:
        names = df["Name"].dropna().unique().tolist()
        names = [n for n in names if str(n).strip()]
    else:
        names = []
        
# 確保一定有選項
if not names:
    names = ["Johnny", "Ashley"]

# 退防：如果 last_name 唔喺最新嘅名單入面，更新佢
if 'last_name' in st.session_state and st.session_state.last_name not in names:
    st.session_state.last_name = names[0]

# --- 側邊欄：個人最佳 (PB) ---
st.sidebar.header("🏆 個人最佳 (PB)")
if not df.empty and df["Time"].notnull().any():
    valid_df = df.dropna(subset=['Time'])
    # 取得每人每個項目的最低秒數對應的索引
    idx = valid_df.groupby(['Name', 'Mode'])['Time'].idxmin()
    pb_df = valid_df.loc[idx, ['Name', 'Mode', 'Time', 'Timestamp']].copy()
    
    # 格式化 Timestamp，只顯示日期 (YYYY-MM-DD)
    pb_df['Date'] = pd.to_datetime(pb_df['Timestamp'], errors='coerce').dt.strftime('%Y-%m-%d')
    
    # 整理顯示格式
    pb_df['Time'] = pb_df['Time'].map('{:,.3f}s'.format)
    
    # 選擇要顯示的欄位並調整順序
    pb_df = pb_df[['Name', 'Mode', 'Time', 'Date']]
    
    st.sidebar.table(pb_df)
else:
    st.sidebar.write("暫無紀錄")

# --- 主要錄入介面 ---
if 'last_name' not in st.session_state:
    st.session_state.last_name = names[0] if names else "Johnny"
if 'last_mode' not in st.session_state:
    st.session_state.last_mode = "3-3-3"

modes = ["3-3-3", "3-6-3", "Cycle"]

name_idx = names.index(st.session_state.last_name) if st.session_state.last_name in names else 0
mode_idx = modes.index(st.session_state.last_mode) if st.session_state.last_mode in modes else 0

with st.form("stacking_form", clear_on_submit=True):
    st.subheader("新增練習紀錄")
    
    c1, c2 = st.columns(2)
    with c1:
        name = st.selectbox("選手", names, index=name_idx)
    with c2:
        mode = st.radio("項目", modes, index=mode_idx, horizontal=True)
    
    # 競技疊杯通常計到小數點後三位
    time_val = st.number_input("成績 (秒)", min_value=0.0, max_value=120.0, value=0.0, step=0.001, format="%.3f")
    
    submit_button = st.form_submit_button(label="🚀 儲存成績", use_container_width=True)

if submit_button:
    if time_val <= 0:
        st.error("時間無效！")
    else:
        timestamp_str = datetime.now(ZoneInfo("Asia/Hong_Kong")).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            # 使用底層 gspread client 直接插入一行。
            # 這樣可以觸發 Google Sheets 的「表格 (Table)」自動擴充功能，保留格式。
            url = st.secrets.connections.gsheets.spreadsheet
            ws = conn.client._client.open_by_url(url).worksheet("Data")
            
            # 準備要加入的新行資料，對應欄位順序 (假設是: Timestamp, Name, Mode, Time)
            row_data = [timestamp_str, name, mode, time_val]
            
            # 傳入 table_range 強制讓 append_row 尋找表格並插入，從而擴展表格的格式 (通常用 "A1" 指向表格的左上角)
            ws.append_row(row_data, table_range="A1")
            
            st.success(f"✅ 已紀錄：{name} - {mode} - {time_val}s")
            
            # 記錄當前選擇，方便下一次不需要重新選擇
            st.session_state.last_name = name
            st.session_state.last_mode = mode
            
            # 清除緩存並重新整理，即時見到新成績
            st.cache_data.clear()
            st.rerun() 
        except Exception as e:
            st.error(f"儲存失敗（請確保 Service Account 有編輯權限）：{e}")

# --- 數據展示 (最近 10 條紀錄) ---
st.divider()
st.subheader("📜 最近紀錄")
if not df.empty:
    display_df = df.sort_values(by="Timestamp", ascending=False).head(10)
    st.dataframe(display_df, use_container_width=True)