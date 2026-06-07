# 政府標案監控系統

自動爬取台灣政府電子採購網（PCC）每日標案，依關鍵字比對後寄送 Gmail 通知，並追蹤得標結果。

## 系統架構

```
backend/              Python 後端（每日排程執行）
├── crawler.py        爬取 PCC 網站招標 / 決標公告
├── sheets.py         Google Sheets 讀寫層
├── notify.py         Gmail 寄信通知
└── main.py           每日流程入口

frontend/             靜態前端（GitHub Pages）
├── index.html        標案瀏覽與搜尋
├── watching.html     追蹤中標案與決標結果
├── keywords.html     關鍵字管理
└── config.js         API 設定

.github/workflows/
├── crawler.yml       每日 08:00（台灣）自動執行後端
└── pages.yml         前端自動部署至 GitHub Pages
```

## 資料流

```
PCC 網站
  ↓ 每日 08:00
crawler.py → sheets.py → Google Sheets（raw 分頁）
                ↓
        比對 keywords 分頁
                ↓ 有符合
        notify.py → Gmail 通知

使用者點信件連結 → PCC 官網查看標案詳情
前端（選用）→ 從 Google Sheets 讀取顯示
```

## 快速設定

### 必要 GitHub Secrets

| Secret | 說明 |
|--------|------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Google Service Account 金鑰 JSON |
| `SPREADSHEET_ID` | Google Sheets 試算表 ID |
| `GMAIL_USER` | 寄件 Gmail 地址 |
| `GMAIL_APP_PASSWORD` | Gmail 應用程式密碼 |

### 關鍵字設定

在 Google Sheets 的 `keywords` 分頁新增關鍵字，或透過前端 `keywords.html` 管理。
爬蟲讀取 `active = TRUE` 的關鍵字進行比對。

## 相關連結

- 前端網站：https://l36991035-cell.github.io/tender-monitor/
- Google Sheets：https://docs.google.com/spreadsheets/d/1kY9-FnRKQxAACcfn1CIb1rYkrlSkYevNbnsvcQBvTB0
- 政府電子採購網：https://web.pcc.gov.tw
