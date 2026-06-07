# Frontend

靜態 HTML 前端，部署於 GitHub Pages，直接讀取 Google Sheets 資料。

## 頁面說明

### `index.html` — 標案瀏覽
- 從 Sheets `raw` 分頁讀取所有標案
- 支援即時搜尋（標案名稱、機關名稱）
- 每頁顯示 50 筆，附分頁導覽
- 可將標案加入追蹤（透過 Apps Script 寫入 `watching` 分頁）

### `watching.html` — 追蹤管理
- 顯示所有追蹤中標案與決標結果
- 支援標記關閉、移除追蹤

### `keywords.html` — 關鍵字管理
- 新增 / 刪除關鍵字
- 切換啟用 / 停用狀態
- 爬蟲每日讀取 `active=TRUE` 的關鍵字進行比對

### `config.js` — 共用設定
```javascript
const CONFIG = {
  SPREADSHEET_ID: '...',    // Google Sheets ID
  GOOGLE_API_KEY: '...',    // 唯讀 API Key（讀取 Sheets）
  APPS_SCRIPT_URL: '...',   // 寫入用 Apps Script 端點
};
```

## 架構說明

- **讀取**：透過 Google Sheets API（公開 API Key）
- **寫入**：透過 Google Apps Script Web App（POST 請求）
- **標案連結**：使用 `redirectPublic?ds=YYYYMMDD&fn=TIQ-1-XXXXXXX.xml` 格式

## 部署

前端由 GitHub Actions（`pages.yml`）自動部署至 GitHub Pages。
推送 `frontend/` 下任何檔案的變更即會觸發重新部署。

網站網址：https://l36991035-cell.github.io/tender-monitor/
