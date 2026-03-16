# 🏆 Stacking Tracker | 競技疊杯練習日誌

這是一個專為競技疊杯（Sport Stacking）愛好者與家長設計的輕量化數據記錄 App。透過 Streamlit 與 Google Sheets 的結合，讓家長能隨時隨地用手機為選手記錄每一分進步。

## ✨ 核心功能
- **快速錄入**：優化手機單手操作介面，快速切換 3-3-3, 3-6-3, Cycle 模式。
- **數據連動**：直接串聯 Google Sheets，數據永久保存，隨時可導出。
- **即時戰績**：自動計算 **PB (Personal Best)** 與 **Ao5 (Average of 5)**。
- **家庭共享**：支持多人名稱切換，全家練習一齊記。

## 🛠️ 技術棧
- **Frontend/Backend**: [Streamlit](https://streamlit.io/)
- **Database**: [Google Sheets](https://www.google.com/sheets/about/) (via `st-gsheets-connection`)
- **Language**: Python 3.9+

## 🚀 快速部署指南

### 1. 準備 Google Sheet
1. 建立一張 Google Sheet，第一行標題必須包含：`Timestamp`, `Name`, `Mode`, `Time`。
2. 點擊右上方 **「共用」**，將權限設為「知道連結的使用者都可以編輯」。
3. 複製該試算表的網址 (URL)。

### 2. 設定 Streamlit Secrets
在 Streamlit Cloud 部署時，請在 **Advanced Settings** -> **Secrets** 中貼入以下內容：

```toml
[connections.gsheets]
spreadsheet = "你的GoogleSheet網址"
