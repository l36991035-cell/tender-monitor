# sheets.py
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pytz

_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
]

RAW_COLS      = ['id', 'name', 'unit', 'date', 'category', 'method', 'fetched_at']
WATCHING_COLS = ['id', 'name', 'unit', 'date', 'category', 'added_at', 'status',
                 'award_date', 'award_price', 'award_vendor', 'last_checked']
KEYWORDS_COLS = ['keyword', 'created_at', 'active']

TZ = pytz.timezone('Asia/Taipei')

_client: gspread.Client | None = None


def get_client() -> gspread.Client:
    global _client
    if _client is None:
        info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
        creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
        _client = gspread.authorize(creds)
    return _client


def _get_sheet(name: str) -> gspread.Worksheet:
    client = get_client()
    spreadsheet_id = os.environ['SPREADSHEET_ID']
    return client.open_by_key(spreadsheet_id).worksheet(name)


def append_raw(records: list[dict]) -> int:
    ws = _get_sheet('raw')
    all_values = ws.get_all_values()

    existing_ids: set[str] = set()
    if len(all_values) > 1:
        id_col = 0  # 'id' is always first column
        existing_ids = {row[id_col] for row in all_values[1:] if row}

    now = datetime.now(TZ).isoformat()
    rows_to_add = [
        [r['id'], r['name'], r['unit'], r['date'],
         r.get('category', ''), r.get('method', ''), now]
        for r in records if r['id'] not in existing_ids
    ]

    if rows_to_add:
        ws.append_rows(rows_to_add, value_input_option='RAW')

    return len(rows_to_add)


def update_award(row_index: int, award_info: dict) -> None:
    ws = _get_sheet('watching')
    now = datetime.now(TZ).isoformat()
    # Single batch update: columns G-K (status, award_date, award_price, award_vendor, last_checked)
    ws.update(
        f'G{row_index}:K{row_index}',
        [['awarded',
          award_info.get('award_date', ''),
          award_info.get('award_price', ''),
          award_info.get('award_vendor', ''),
          now]],
        value_input_option='RAW',
    )


def cleanup_raw(days: int = 90) -> int:
    raw_ws = _get_sheet('raw')
    watching_ws = _get_sheet('watching')

    all_values = raw_ws.get_all_values()
    if len(all_values) <= 1:
        return 0

    watching_ids = {r['id'] for r in watching_ws.get_all_records()}
    headers = all_values[0]
    date_col = headers.index('date')
    id_col = headers.index('id')
    cutoff = datetime.now(TZ).date() - timedelta(days=days)

    rows_to_delete = []
    for i, row in enumerate(all_values[1:], start=2):
        if not row or not row[date_col]:
            continue
        try:
            row_date = datetime.strptime(row[date_col], '%Y-%m-%d').date()
        except ValueError:
            continue
        if row_date < cutoff and row[id_col] not in watching_ids:
            rows_to_delete.append(i)

    # Delete contiguous ranges from bottom to top to avoid index shifting
    if rows_to_delete:
        sorted_rows = sorted(rows_to_delete, reverse=True)
        # Group into contiguous runs
        groups = []
        start = end = sorted_rows[0]
        for idx in sorted_rows[1:]:
            if idx == end - 1:
                end = idx
            else:
                groups.append((end, start))
                start = end = idx
        groups.append((end, start))
        for first, last in groups:
            raw_ws.delete_rows(first, last)

    return len(rows_to_delete)


def get_watching_tracking() -> list[dict]:
    ws = _get_sheet('watching')
    records = ws.get_all_records()
    result = []
    for i, row in enumerate(records, start=2):  # row 1 is header; data starts at 2
        if row.get('status') == 'tracking':
            row['_row_index'] = i
            result.append(row)
    return result


def get_keywords() -> list[str]:
    ws = _get_sheet('keywords')
    records = ws.get_all_records()
    return [r['keyword'] for r in records if str(r.get('active', '')).upper() == 'TRUE']
