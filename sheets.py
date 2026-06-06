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
