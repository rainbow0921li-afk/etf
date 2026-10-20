# 📈 0050 元大台灣50 ETF 投資看板 (手機響應式版)

專為 **0050（元大台灣卓越50）** 打造的極簡、現代化 ETF 投資平台。採用 **方案 A（純靜態 + 自動化排程）** 架構，**完全免費、零伺服器維護成本**，手機隨時開啟秒載入！

---

## 🌟 核心特色功能

1. **📱 手機優先響應式設計 (Mobile First)**
   * 針對 iPhone 與 Android 手機最佳化，支援加入手機桌面主畫面（PWA 體驗）。
   * 支援台股紅漲綠跌直覺視覺化、深色金融科技主題。
2. **⚡ 即時行情報價與 52 週進度條**
   * 當日開盤、昨收、最高、最低、成交量與成交金額。
   * 52 週最高與最低價格區間進度條。
3. **📊 互動式價格走勢圖表**
   * 支援切換 1M（近1月）、3M、6M、1Y、3Y 週期。
   * 支援手機手指觸控十字游標檢視歷史價格。
4. **💰 定期定額 (DCA) 歷史回測試算機**
   * 投資人最愛功能！可自訂每月扣款金額（如 3,000 / 5,000 / 10,000 元）與投資年限（1~3年）。
   * 採用真實歷史還原股價（含股息再投資），即時計算**累積本金、目前總資產、累積獲利與投資報酬率**。
5. **🧩 成分股與產業權重透視**
   * 視覺化產業佔比橫條（半導體、金融保險、電腦周邊等）。
   * 前十大成分股卡片（台積電、聯發科、鴻海、廣達等）展示權重、股價、本益比、殖利率。
   * 支援展開全部 50 檔成分股並提供即時關鍵字搜尋。
6. **💵 歷年配息與填息天數紀錄**
   * 歷年半年配金額、當期殖利率、填息天數與填息成功狀態。
7. **🤖 GitHub Actions 自動每日更新**
   * 每個營業日下午 15:30（收盤盤後）自動執行 Python 爬蟲更新 `data/0050.json`。

---

## 🚀 部署到雲端（讓手機隨時隨地能看）

### 步驟 1：建立 GitHub 儲存庫並上傳
在您的電腦終端機將此資料夾推送到您的 GitHub：
```bash
git branch -M main
git remote add origin https://github.com/<您的GitHub帳號>/<您的儲存庫名稱>.git
git push -u origin main
```

---

### 步驟 2：選擇雲端平台免費發布（推薦 Vercel 或 Cloudflare Pages）

#### 推薦方式 A：Vercel（最推薦，1 分鐘搞定）
1. 前往 [Vercel 官網](https://vercel.com/)，使用 GitHub 帳號免費登入。
2. 點選 **"Add New..."** -> **"Project"**。
3. 選擇您剛剛建立的 `etf-0050` 儲存庫，點擊 **"Import"**。
4. 設定保持預設（Framework Preset 選 `Other`），點擊 **"Deploy"**。
5. 大約 15 秒後即可獲得一組免費的專屬 HTTPS 網址（例如：`https://etf-0050.vercel.app`）！
6. 用手機打開這個網址即可隨時瀏覽！

#### 方式 B：GitHub Pages（完全原生於 GitHub）
1. 在您的 GitHub 儲存庫頁面點擊 **"Settings"** -> 側邊欄 **"Pages"**。
2. 在 **"Branch"** 選擇 `main`，資料夾選擇 `/ (root)`，點擊 **"Save"**。
3. 等待 1 分鐘，網址即可於 `https://<您的帳號>.github.io/<專案名稱>/` 上線。

---

### 步驟 3：設定自動更新權限 (GitHub Actions)
為了讓 GitHub Actions 每天自動抓取最新資料並提交回儲存庫：
1. 進入 GitHub 儲存庫的 **Settings** -> **Actions** -> **General**。
2. 捲動至最下方的 **"Workflow permissions"**。
3. 勾選 **"Read and write permissions"**，點擊 **Save**。
4. 之後每個營業日下午 15:30（台灣時間），系統就會自動抓取最新盤後資料更新網頁！

---

## 💻 本地測試與資料更新

### 手動執行爬蟲更新資料
本專案採用 **零依賴設計 (Zero-Dependency)**，只需 Python 3 內建標準庫，無需安裝額外套件：
```bash
python3 scripts/fetch_data.py
```

### 本地啟動預覽
```bash
python3 -m http.server 8000
```
瀏覽器開啟：`http://localhost:8000`

---

## 📁 目錄結構

```text
├── .github/
│   └── workflows/
│       └── update-data.yml   # 營業日 15:30 自動更新資料排程
├── data/
│   └── 0050.json             # 爬蟲產出的 0050 核心資料集
├── scripts/
│   └── fetch_data.py         # Python 爬蟲（證交所 OpenAPI + Yahoo Finance）
├── index.html                # 手機響應式前端主頁面 (Tailwind CSS + Chart.js)
├── .gitignore
└── README.md
```
