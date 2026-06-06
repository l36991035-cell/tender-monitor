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
