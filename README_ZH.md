> **🌐 Language / 語言**: [English](README.md) | 繁體中文

# ⏱️ Stacking Tracker | 競技疊杯練習日誌

專為競技疊杯（Sport Stacking）愛好者與家長設計的輕量化數據記錄 App。透過 Streamlit 與 Google Sheets 的結合，讓家長能隨時隨地用手機為選手記錄每一分進步。

## ✨ 核心功能

### 📈 今日練習進度
- 自動追蹤每日練習達標率（嚴格 / 寬鬆兩種計法）
- 根據 Google Sheets `Goals` 分頁設定的目標秒數，即時計算成功次數
- 每位選手獨立顯示進度

### ⚡ 快速記錄模式 (批次同步)
- 專為極速連續接戰（3-3-3 項目）設計的選用模式
- 練習成績先暫存於本地「待上傳記錄」池，完全無網絡延遲
- 一鍵將所有暫存紀錄批次同步至雲端（使用高效能 `append_rows` 優化）

### 📊 Ao5 (Average of 5)
- 自動計算最近 5 次有效成績的平均值
- 去掉最快與最慢各一次，取中間三次平均（WSSA 標準）
- 按項目分組顯示

### 🏆 個人最佳 (PB)
- 自動追蹤每位選手在每個項目的最快成績
- 按項目分組，顯示 PB 及達成日期

### ❌ 失誤 / DNF 標記
- 支援「跌杯」等失誤情況，標記為 Scratch / DNF
- DNF 成績不計入 PB 與 Ao5，但保留時間作參考
- 達標率提供嚴格（含 DNF）與寬鬆（排除 DNF）兩種計法

### 🧒 兒童友好介面
- 超大按鈕設計（綠色成功 / 紅色失誤），4 歲小朋友都可以自己操作
- 手機數字鍵盤優化
- 儲存後自動清空輸入框
- 使用 `@st.fragment` 隔離輸入區，切換選手/項目不會重新載入整個頁面

### 📜 紀錄總覽
- 今日紀錄逐條顯示
- 過往紀錄按日期 + 項目分組摘要，包含總次數、DNF 次數、最快成績

### 🌐 雙語支援
- 自動偵測瀏覽器語言，預設繁體中文或英文
- 側邊欄可隨時手動切換語言，切換後不影響已有數據
- 所有介面文字（標題、按鈕、訊息、欄位名）即時更新

## 🛠️ 技術棧
- **Frontend/Backend**: [Streamlit](https://streamlit.io/) 1.55+
- **Database**: [Google Sheets](https://www.google.com/sheets/about/) (via `st-gsheets-connection`)
- **Language**: Python 3.9+

## 🚀 快速部署指南

### 1. 準備 Google Sheet

建立一張 Google Sheet，包含以下 **3 個分頁 (Worksheet)**：

#### `Data` 分頁（必須）
第一行標題：

| Timestamp | Name | Mode | Time | IsScratch |
|-----------|------|------|------|-----------|

#### `Players` 分頁（建議）
第一行標題：

| Name |
|------|
| Johnny |
| Ashley |

#### `Goals` 分頁（建議）
第一行標題：

| Name | Mode | TargetTime |
|------|------|------------|
| All | 3-3-3 | 3.999 |
| All | 3-6-3 | 5.999 |
| Johnny | 3-3-3 | 3.500 |

- `Name` 填 `All` 代表適用所有選手；填特定名字則為該選手專屬目標
- `TargetTime` 為達標秒數上限（≤ 此秒數即為達標）

### 2. 設定 Streamlit Secrets

在 Streamlit Cloud 部署時，請在 **Advanced Settings** → **Secrets** 中貼入：

```toml
[connections.gsheets]
spreadsheet = "你的GoogleSheet網址"
```

### 3. 本地開發

```bash
# 建立虛擬環境
python -m venv venv
venv\Scripts\activate  # Windows

# 安裝依賴
pip install streamlit streamlit-gsheets-connection pandas

# 設定 secrets
mkdir .streamlit
# 將 secrets.toml 放入 .streamlit/ 目錄

# 啟動
streamlit run streamlit_app.py
```

## 📁 專案結構

```
stacking-tracker/
├── streamlit_app.py    # 主應用程式
├── requirements.txt    # Python 依賴
├── .gitignore          # Git 忽略規則
├── .streamlit/
│   └── secrets.toml    # Google Sheets 連線設定 (不上傳)
├── README.md           # 英文說明文檔
└── README_ZH.md        # 中文說明文檔
```
