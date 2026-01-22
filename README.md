#  食分好找 (Foodsaver)

> **「省錢、省時」並「減少浪費」 —— 您的全方位即期品智慧採買助理**

![Python](https://img.shields.io/badge/Python-3.x-blue.svg) ![Flask](https://img.shields.io/badge/Backend-Flask-green.svg) ![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg) ![AI](https://img.shields.io/badge/AI-LLaMA-orange.svg)

##  專案背景

在台灣，便利商店與超市的即期品資訊（如 i珍食、友善食光）往往散落在不同的 App 或平台中，導致使用者查詢耗時且難以規劃。

**食分好找 (Foodsaver)** 是一個跨超商整合平台，透過模擬真實超商資料，將零散的資訊整合為直觀的地圖與列表，旨在解決「食物浪費」問題，同時幫助預算有限的族群輕鬆實踐惜食生活，兼具省錢又省時的功效。

---

##  核心功能

### 1. 跨商家資訊整合
* **整合多品牌**：支援 7-Eleven、全家、OK、萊爾富等不同品牌的即期品查詢。
* **突破限制**：打破單一品牌 App 的限制，一次掌握周邊所有優惠；同時支援依類別、價格、剩餘數量篩選商品。

### 2.  動態決策地圖
* **視覺化呈現**：以互動地圖顯示周邊店家。
* **直觀資訊**：圓圈大小代表「剩餘數量」，顏色區分「不同品牌」。
* **定位服務**：整合 `Nominatim API`，支援地標搜尋與座標轉換，一鍵串接 Google Map 導航至目標店家。

### 3.  AI 智慧助理
> "今天晚餐吃什麼？"
* 內建自然語言互動功能（串接 **LLaMA** 模型）。
* 依據目前的庫存與您的位置提供建議，不僅省錢，還能解決選擇障礙。

### 4.  個人化會員體驗
* **喜好清單**：會員可建立專屬清單，系統自動推送折扣通知。
* **數據洞察**：透過視覺化圖表分析您的採買習慣與省錢趨勢。

---

##  開發技術

本專案使用 Python 開發，環境為 Visual Studio Code，並採用輕量化的架構以便於部署。

```python
# Backend & Framework
Framework = "Flask (Python)"
Database  = "SQLite"

# Frontend & Interaction
Frontend  = ["HTML", "JavaScript"]
Maps      = ["OpenStreetMap (Nominatim)", "Google Map API"]

# AI Integration
AI_Model  = "LLaMA (via OpenRouter.ai)"
SDK       = "OpenAI Python SDK"

---

##  系統流程

### 1. 訪客模式
快速瀏覽首頁的即時推薦清單，查看價格、超商距離與評價。

### 2.  會員模式
享有「喜好清單」功能，系統主動推薦折扣商品並發送即時通知。
