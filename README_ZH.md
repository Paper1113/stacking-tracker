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
- 內建 **互動式歷史趨勢圖 (Line Chart)**，將進步軌跡視覺化
- 按項目分組，預設摺疊顯示，瀏覽更清爽
- 每個項目會按選手顯示各自 Top 5 成績

### 🛡️ 穩定性與快取管理
- **手動重新整理**：側邊欄新增「重新整理」按鈕，讓使用者能隨時清空 Streamlit 快取並強制抓取雲端最新資料
- **API 自動重試**：導入 `tenacity` 套件，所有與 Google Sheets 的連線遇到網路不穩時，皆會自動在背景安全重試（最多 3 次），避免 App 崩潰
- **穩定記錄定位**：每筆資料會有唯一 `RecordId`，即使時間/選手/項目重複，修改與刪除仍可精準命中正確記錄

### 🔄 CI/CD 與自動化測試
- 專案受 **GitHub Actions** 自動化工作流程保護
- 核心計算邏輯（如 Ao5 規則）皆有 **pytest** 單元測試覆蓋，並在每次 Push 或 PR 時自動執行驗證

### ❌ 失誤 / DNF 標記
- 支援「跌杯」等失誤情況，標記為 Scratch / DNF
- DNF 成績不計入 PB 與 Ao5，但保留時間作參考
- 達標率提供嚴格（含 DNF）與寬鬆（排除 DNF）兩種計法

### 🧒 兒童友好介面
- 超大按鈕設計（綠色成功 / 紅色失誤），4 歲小朋友都可以自己操作
- 使用自訂 Streamlit 元件優化小數輸入（iOS Safari 會顯示含小數點的數字鍵盤）
- 儲存後自動清空輸入框
- 清晰顯示目前選擇（選手 + 項目），減少誤按

### 📜 紀錄總覽
- 今日紀錄按項目分組，顯示逐筆詳細紀錄（時間戳、選手、成績、DNF 標記）
- 過往紀錄改為按 **選手 → 項目** 分組，兩層皆預設摺疊
- 每個過往項目會以**按日摘要**顯示：日期、總次數（`總次數 (DNF: x)`）、失誤率、最快
- **修改與刪除**：置於主頁「最近紀錄」區塊，可編輯或刪除今日紀錄
- 刪除前會有二次確認提示，避免誤刪

### 🌐 雙語支援
- 自動偵測瀏覽器語言，預設繁體中文或英文
- 側邊欄可隨時手動切換語言，切換後不影響已有數據
- 所有介面文字（標題、按鈕、訊息、欄位名）即時更新

## 🛠️ 技術棧
- **Frontend/Backend**: [Streamlit](https://streamlit.io/) 1.55+
- **Database**: [Google Sheets](https://www.google.com/sheets/about/) (via `st-gsheets-connection`)
- **Resilience**: `tenacity` (API 自動重試)
- **Testing**: `pytest`, GitHub Actions
- **Language**: Python 3.9+

## 🚀 快速部署指南

### 1. 準備 Google Sheet

建立一張 Google Sheet，包含以下 **3 個分頁 (Worksheet)**：

#### `Data` 分頁（必須）
第一行標題：

| Timestamp | Name | Mode | Time | IsScratch | RecordId |
|-----------|------|------|------|-----------|----------|

- `RecordId` 為每筆紀錄的唯一識別碼；舊資料即使未有此欄位，App 亦會自動相容處理

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
pip install streamlit st-gsheets-connection pandas pytest tenacity

# 設定 secrets
mkdir .streamlit
# 將 secrets.toml 放入 .streamlit/ 目錄

# 啟動
streamlit run streamlit_app.py
```

## 📁 專案結構

```text
stacking-tracker/
├── .github/
│   └── workflows/
│       └── test.yml    # GitHub Actions 自動化測試流程
├── streamlit_app.py    # 主應用程式 (負責 UI 佈局)
├── config.json         # 專案常數設定 (例: 支援項目、資料暫存頻率)
├── i18n.json           # 外部化的多國語系翻譯檔
├── requirements.txt    # Python 依賴清單
├── .gitignore          # Git 忽略規則
├── tests/              # 單元測試資料夾
│   ├── test_stats.py   # 針對 Ao5 與資料處理邏輯的 pytest
│   └── test_record_id.py # RecordId 精準定位與相容性測試
├── utils/              # 獨立功能模組
│   ├── data_manager.py # Google Sheets 連線與存取邏輯
│   ├── i18n.py         # 語系載入與切換邏輯
│   └── stats.py        # Ao5、PB 與每日進度計算邏輯
├── .streamlit/
│   └── secrets.toml    # Google Sheets 連線設定 (不上傳)
├── README.md           # 英文說明文檔
└── README_ZH.md        # 中文說明文檔
```
