# crawler.py
import re
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime
import pytz

BASE_URL = 'https://web.pcc.gov.tw'
TZ = pytz.timezone('Asia/Taipei')

_HEADERS = {
    'User-Agent': 'Mozilla/5.0',
}

_LINK_RE = re.compile(r'[\[]*(?:<\d+>\s*)?(.+?)：(.+?)\s+-\s+(.+?)[\]]*\s*$')


def _to_roc_date(d: date) -> str:
    roc_year = d.year - 1911
    return f'{roc_year}年{d.month:02d}月{d.day:02d}日'


def _parse_tenders(soup: BeautifulSoup, target_date: date) -> list[dict]:
    tenders: list[dict] = []
    current_section = ''
    seen: set[str] = set()

    for el in soup.find_all(['a', 'table']):
        if el.name == 'a':
            href = el.get('href', '')

            if el.get('id') and '公告' in el.get('id', ''):
                current_section = el.get('id', '')
            elif href.startswith('#') and '公告' in href:
                current_section = href.lstrip('#')

            elif href.startswith('TIQ-'):
                record_id = href.replace('.xml', '')
                if record_id not in seen:
                    link_text = el.get_text(' ', strip=True)
                    m = _LINK_RE.match(link_text)
                    if m:
                        seen.add(record_id)
                        tenders.append({
                            'id':     record_id,
                            'name':   m.group(3).strip(),
                            'unit':   m.group(1).strip(),
                            'date':   target_date.isoformat(),
                            'method': current_section,
                        })

        elif el.name == 'table' and 'tenderCase' in (el.get('class') or []):
            link = el.find('a', class_='tenderLinkPublish')
            if not link:
                continue
            href = link.get('href', '')
            if not href.startswith('TIQ-'):
                continue
            link_text = link.get_text(' ', strip=True)
            m = _LINK_RE.match(link_text)
            if not m:
                continue
            record_id = href.replace('.xml', '')
            if record_id not in seen:
                seen.add(record_id)
                tenders.append({
                    'id':     record_id,
                    'name':   m.group(3).strip(),
                    'unit':   m.group(1).strip(),
                    'date':   target_date.isoformat(),
                    'method': current_section,
                })

    return tenders


def fetch_today_new(target_date: date | None = None) -> list[dict]:
    if target_date is None:
        target_date = datetime.now(TZ).date()
    resp = requests.get(
        f'{BASE_URL}/prkms/tender/common/noticeDate/readPublish',
        params={'dateStr': _to_roc_date(target_date)},
        headers=_HEADERS,
        timeout=60,
    )
    if resp.status_code == 500:
        print(f'[crawler] PCC {target_date} 無資料（500），視為 0 筆')
        return []
    resp.raise_for_status()
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')
    return _parse_tenders(soup, target_date)


def debug_parse(target_date: date | None = None) -> None:
    if target_date is None:
        target_date = datetime.now(TZ).date()
    resp = requests.get(
        f'{BASE_URL}/prkms/tender/common/noticeDate/readPublish',
        params={'dateStr': _to_roc_date(target_date)},
        headers=_HEADERS,
        timeout=60,
    )
    resp.raise_for_status()
    resp.encoding = 'utf-8'
    soup = BeautifulSoup(resp.text, 'html.parser')
    tenders = _parse_tenders(soup, target_date)
    print(f'[debug] {target_date}: {len(tenders)} tenders')
    for t in tenders[:10]:
        print(f'  {t["id"]}: {t["unit"]} / {t["name"][:40]}')
