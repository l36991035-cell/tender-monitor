# crawler.py
import time
import requests
from datetime import date, timedelta, datetime
import pytz

import sheets

BASE_URL = 'https://pcc.g0v.ronny.tw'
_DELAY = 0.5

TZ = pytz.timezone('Asia/Taipei')


def fetch_date(target_date: date) -> int:
    url = f'{BASE_URL}/index/date/{target_date.isoformat()}'
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    records = [
        {
            'id':       item.get('id', ''),
            'name':     item.get('name', ''),
            'unit':     item.get('unit', ''),
            'date':     item.get('date', target_date.isoformat()),
            'category': item.get('attr', ''),
            'method':   item.get('radard', ''),
        }
        for item in data.get('records', [])
    ]

    return sheets.append_raw(records)


def fetch_today() -> int:
    today = datetime.now(TZ).date()
    return fetch_date(today)


def fetch_backfill(days: int) -> int:
    today = datetime.now(TZ).date()
    total = 0
    for i in range(days, 0, -1):
        d = today - timedelta(days=i)
        count = fetch_date(d)
        total += count
        time.sleep(_DELAY)
    return total
