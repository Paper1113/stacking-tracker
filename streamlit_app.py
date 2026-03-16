import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

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
    
    # 處理被 Google Sheets 自動轉換為日期的 Mode (例如 "2003-6-3" 變回 "3-6-3")
    if "Mode" in df.columns:
        df["Mode"] = df["Mode"].astype(str)
        df["Mode"] = df["Mode"].str.lstrip("'")  # 清理可能用作保護字元的單引號
        df.loc[df["Mode"].str.contains("2003-3|2003-03", na=False), "Mode"] = "3-3-3"
        df.loc[df["Mode"].str.contains("2003-6|2003-06", na=False), "Mode"] = "3-6-3"
        
    # 強制將 Time 轉做數字，方便計 PB
    df["Time"] = pd.to_numeric(df["Time"], errors='coerce')
except Exception as e:
    st.error(f"讀取失敗（請檢查 Sheet 名稱是否為 Data）：{e}")
    df = pd.DataFrame(columns=["Timestamp", "Name", "Mode", "Time"])

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
    st.session_state.last_name = "Johnny"
if 'last_mode' not in st.session_state:
    st.session_state.last_mode = "3-3-3"

names = ["Johnny", "Ashley"]
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
        new_entry = pd.DataFrame([{
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Name": name,
            "Mode": mode,
            "Time": time_val
        }])
        
        try:
            # 合併舊數據同新數據
            updated_df = pd.concat([df, new_entry], ignore_index=True)
            
            # 準備寫入：為防止 Google Sheets 自動將 "3-3-3" 轉回日期，加上單引號保護
            df_to_save = updated_df.copy()
            if "Mode" in df_to_save.columns:
                df_to_save["Mode"] = df_to_save["Mode"].apply(
                    lambda x: f"'{x}" if isinstance(x, str) and x in ["3-3-3", "3-6-3"] else x
                )
                
            # 寫入時同樣指定 worksheet="Data"
            conn.update(worksheet="Data", data=df_to_save)
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