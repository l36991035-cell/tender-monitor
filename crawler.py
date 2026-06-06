# crawler.py
import time
import requests
from datetime import date, timedelta, datetime
import pytz

import sheets

BASE_URL = 'https://pcc.g0v.ronny.tw'
_DELAY = 0.5

TZ = pytz.timezone('Asia/Taipei')


def _get_award_info(tender_id: str) -> dict | None:
    if '_' not in tender_id:
        return None
    unit_id, job_number = tender_id.split('_', 1)

    resp = requests.get(
        f'{BASE_URL}/tender/detail',
        params={'unit_id': unit_id, 'job_number': job_number},
        timeout=30,
    )
    resp.raise_for_status()
    award = resp.json().get('detail', {}).get('award', {})

    if not award or not award.get('award_date'):
        return None

    return {
        'award_date':   award.get('award_date', ''),
        'award_price':  award.get('award_price', ''),
        'award_vendor': award.get('award_vendor', ''),
    }


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
