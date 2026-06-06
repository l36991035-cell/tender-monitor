# sheets.py
import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import pytz

_SCOPES = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive',
]

RAW_COLS      = ['id', 'name', 'unit', 'date', 'category', 'method', 'fetched_at']
WATCHING_COLS = ['id', 'name', 'unit', 'date', 'category', 'added_at', 'status',
                 'award_date', 'award_price', 'award_vendor', 'last_checked']
KEYWORDS_COLS = ['keyword', 'created_at', 'active']

TZ = pytz.timezone('Asia/Taipei')


def get_client() -> gspread.Client:
    info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
    creds = Credentials.from_service_account_info(info, scopes=_SCOPES)
    return gspread.authorize(creds)


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
    # Column positions (1-indexed) based on WATCHING_COLS order:
    # 1=id, 2=name, 3=unit, 4=date, 5=category, 6=added_at, 7=status,
    # 8=award_date, 9=award_price, 10=award_vendor, 11=last_checked
    ws.update_cell(row_index, 8,  award_info.get('award_date', ''))
    ws.update_cell(row_index, 9,  award_info.get('award_price', ''))
    ws.update_cell(row_index, 10, award_info.get('award_vendor', ''))
    ws.update_cell(row_index, 7,  'awarded')
    ws.update_cell(row_index, 11, now)


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

    for row_idx in sorted(rows_to_delete, reverse=True):
        raw_ws.delete_rows(row_idx)

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
