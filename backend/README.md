# Backend

每日自動爬取政府採購網標案、比對關鍵字、寄送 Gmail 通知。

## 模組說明

### `main.py` — 每日流程入口
GitHub Actions 執行的進入點，依序執行三個步驟：
1. 爬取今日標案 → 寫入 Sheets → 比對關鍵字 → 寄信
2. 查核追蹤中標案是否已決標 → 更新 Sheets → 寄信
3. 清除 90 天以上的舊標案記錄

```bash
# 執行今日排程
python main.py

# 回填過去 N 天資料
python main.py --backfill 7
```

### `crawler.py` — 爬蟲
從 `web.pcc.gov.tw` 的 `readPublish` 端點爬取每日公告，同一頁面同時包含：
- **TIQ**（招標公告）：解析後寫入 Sheets `raw` 分頁
- **BDM**（決標公告）：與 `watching` 分頁比對，更新決標資訊

決標詳細頁 URL 格式：`redirectPublic?ds=YYYYMMDD&fn=BDM-1-XXXXXXX.xml`

### `sheets.py` — Google Sheets 讀寫層
管理三個工作表：

| 工作表 | 用途 |
|--------|------|
| `raw` | 每日爬回的所有標案（保留 90 天） |
| `watching` | 使用者追蹤中的標案與決標結果 |
| `keywords` | 關鍵字清單（`active=TRUE` 才啟用） |

### `notify.py` — Gmail 通知
- **關鍵字符合**：當日新標案中有符合關鍵字者，寄送摘要信
- **決標通知**：追蹤中標案有決標結果時，寄送決標詳情

## 環境變數

| 變數 | 說明 |
|------|------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Service Account 金鑰（完整 JSON 字串） |
| `SPREADSHEET_ID` | Google Sheets ID |
| `GMAIL_USER` | Gmail 地址（寄件人 = 收件人） |
| `GMAIL_APP_PASSWORD` | Gmail 應用程式密碼 |

## 本機執行

```powershell
$env:SPREADSHEET_ID = "1kY9-FnRKQxAACcfn1CIb1rYkrlSkYevNbnsvcQBvTB0"
$env:GOOGLE_SERVICE_ACCOUNT_JSON = Get-Content "path/to/key.json" -Raw
$env:GMAIL_USER = "your@gmail.com"
$env:GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
python main.py
```
