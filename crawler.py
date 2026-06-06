# crawler.py
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime
import pytz

import sheets

BASE_URL = 'https://web.pcc.gov.tw'
_DELAY = 1.0
TZ = pytz.timezone('Asia/Taipei')

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Referer': f'{BASE_URL}/prkms/tender/common/noticeDate/indexNoticeDate',
}


def _to_roc_date(d: date) -> str:
    roc_year = d.year - 1911
    return f'{roc_year}年{d.month:02d}月{d.day:02d}日'


def fetch_date(target_date: date) -> int:
    resp = requests.get(
        f'{BASE_URL}/prkms/tender/common/noticeDate/readPublish',
        params={'dateStr': _to_roc_date(target_date)},
        headers=_HEADERS,
        timeout=60,
    )
    resp.raise_for_status()
    resp.encoding = 'utf-8'

    soup = BeautifulSoup(resp.text, 'html.parser')
    records = []
    current_method = ''

    for el in soup.find_all(['a', 'table']):
        if el.name == 'a' and '公告' in el.get('id', ''):
            current_method = el.get('id', '')
        elif el.name == 'table' and 'tenderCase' in (el.get('class') or []):
            link = el.find('a', class_='tenderLinkPublish')
            if not link:
                continue
            link_text = link.get_text(' ', strip=True)
            m = re.match(r'<\d+>\s*(.+?)：(.+?)\s*-\s*(.+)', link_text)
            if m:
                records.append({
                    'id':       link.get('href', '').replace('.xml', ''),
                    'name':     m.group(3).strip(),
                    'unit':     m.group(1).strip(),
                    'date':     target_date.isoformat(),
                    'category': '',
                    'method':   current_method,
                })

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


def _get_award_info(tender_id: str) -> dict | None:
    # Award checking via official website not yet implemented.
    # pcc.g0v.ronny.tw (original API) is permanently down.
    return None


def check_awards() -> int:
    tracking = sheets.get_watching_tracking()
    updated = 0
    for tender in tracking:
        try:
            award_info = _get_award_info(tender['id'])
            if award_info:
                sheets.update_award(tender['_row_index'], award_info)
                updated += 1
        except Exception as e:
            print(f'[check_awards] error for {tender["id"]}: {e}')
        time.sleep(_DELAY)
    return updated
