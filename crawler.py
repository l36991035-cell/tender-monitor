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

# Matches both "<1> unit：case_no - name" (TIQ) and "unit：case_no - name" (BDM, no leading number)
_LINK_RE = re.compile(r'(?:<\d+>\s*)?(.+?)：(.+?)\s*-\s*(.+)')


def _to_roc_date(d: date) -> str:
    roc_year = d.year - 1911
    return f'{roc_year}年{d.month:02d}月{d.day:02d}日'


def _norm(s: str) -> str:
    """Normalize whitespace for matching between TIQ and BDM entries."""
    return ' '.join(s.split())


def _parse_readpublish(soup: BeautifulSoup, target_date: date) -> tuple[list[dict], list[dict]]:
    """
    Parse a readPublish page into (tenders, awards).

    The page mixes 招標公告 (TIQ-…) and 決標公告 (BDM-…) sections.
    We track the current section via anchor id, then split by href prefix.

    Two parsing paths for awards:
    - Primary: BDM inside a <table class="tenderCase"> (same structure as TIQ)
    - Fallback: bare <a href="BDM-…"> link outside tenderCase (different markup)
    """
    tenders: list[dict] = []
    awards: list[dict] = []
    current_section = ''
    seen_bdm: set[str] = set()

    for el in soup.find_all(['a', 'table']):
        # Track which section we are in
        if el.name == 'a' and el.get('id') and '公告' in el.get('id', ''):
            current_section = el.get('id', '')

        # Primary path: tenderCase table (used by TIQ; may also be used by BDM)
        elif el.name == 'table' and 'tenderCase' in (el.get('class') or []):
            link = el.find('a', class_='tenderLinkPublish')
            if not link:
                continue
            href = link.get('href', '')
            link_text = link.get_text(' ', strip=True)
            m = _LINK_RE.match(link_text)
            if not m:
                continue
            record_id = href.replace('.xml', '')

            if href.startswith('TIQ-'):
                tenders.append({
                    'id':       record_id,
                    'name':     m.group(3).strip(),
                    'unit':     m.group(1).strip(),
                    'date':     target_date.isoformat(),
                    'category': '',
                    'method':   current_section,
                })
            elif href.startswith('BDM-') and _is_award_section(current_section):
                seen_bdm.add(record_id)
                awards.append(_make_award(record_id, m, target_date))

        # Fallback path: bare BDM link not wrapped in tenderCase
        # (find_all visits nested <a> elements too, so seen_bdm prevents double-counting)
        elif (
            el.name == 'a'
            and _is_award_section(current_section)
            and el.get('href', '').startswith('BDM-')
        ):
            href = el.get('href', '')
            record_id = href.replace('.xml', '')
            if record_id in seen_bdm:
                continue
            link_text = el.get_text(' ', strip=True)
            m = _LINK_RE.match(link_text)
            if m:
                seen_bdm.add(record_id)
                awards.append(_make_award(record_id, m, target_date))

    return tenders, awards


def _is_award_section(section_id: str) -> bool:
    """True for 決標公告 section; false for 無法決標公告 and all 招標 sections."""
    return '決標' in section_id and '無法' not in section_id


def _make_award(bdm_id: str, m: re.Match, award_date: date) -> dict:
    return {
        'bdm_id':      bdm_id,
        'unit':        m.group(1).strip(),
        'case_number': m.group(2).strip(),
        'name':        m.group(3).strip(),
        'award_date':  award_date.isoformat(),
    }


def _get_bdm_detail(bdm_id: str, award_date_iso: str, session: requests.Session) -> dict:
    """
    Fetch award details (date, price, vendor) via the redirectPublic endpoint.

    JS on readPublish rewrites each tenderLinkPublish href at page load:
      redirectPublic?ds=YYYYMMDD&fn=BDM-1-XXXXXXX.xml
    award_date_iso is the date the BDM appeared on readPublish (e.g. '2026-06-05').
    """
    ds = award_date_iso.replace('-', '')   # '20260605'
    try:
        resp = session.get(
            f'{BASE_URL}/prkms/tender/common/noticeDate/redirectPublic',
            params={'ds': ds, 'fn': f'{bdm_id}.xml'},
            headers=_HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        if 'D0001' in resp.text or '網址不存在' in resp.text or '找不到標案' in resp.text:
            return {}

        soup = BeautifulSoup(resp.text, 'html.parser')
        result: dict[str, str] = {}
        label_map = {
            '決標日期': 'award_date',
            '決標金額': 'award_price',
            '得標廠商': 'award_vendor',
            '廠商名稱': 'award_vendor',   # fallback label used on some pages
        }
        for row in soup.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            for i, cell in enumerate(cells):
                label = cell.get_text(strip=True)
                for key, field in label_map.items():
                    if key in label and i + 1 < len(cells) and field not in result:
                        raw = cells[i + 1].get_text(strip=True)
                        result[field] = _clean_award_field(field, raw)
        return result
    except Exception as e:
        print(f'[bdm_detail] {bdm_id}: {e}')
        return {}


def _clean_award_field(field: str, raw: str) -> str:
    if field == 'award_price':
        # "5,600,000元伍佰陸拾萬元" → "5,600,000"
        m = re.match(r'[\d,]+', raw)
        return m.group() if m else raw
    if field == 'award_date':
        # ROC "115/05/26" → ISO "2026-05-26"
        m = re.match(r'(\d+)/(\d+)/(\d+)', raw)
        if m:
            return f'{int(m.group(1))+1911}-{m.group(2)}-{m.group(3)}'
    return raw


# ── Public API ────────────────────────────────────────────────────────────────

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
    tenders, _ = _parse_readpublish(soup, target_date)
    return sheets.append_raw(tenders)


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


def check_awards(lookback_days: int = 14) -> int:
    """
    Scan the last `lookback_days` days of 決標公告 and update any matching
    'tracking' tenders in the watching sheet to 'awarded'.

    Matching is done by normalised (unit, name) since case_number is not
    currently stored in the watching sheet.
    """
    tracking = sheets.get_watching_tracking()
    if not tracking:
        return 0

    # Build lookup: (unit, name) → watching row
    watching_index: dict[tuple[str, str], dict] = {
        (_norm(t['unit']), _norm(t['name'])): t
        for t in tracking
    }

    session = requests.Session()
    today = datetime.now(TZ).date()
    updated = 0

    for days_back in range(lookback_days):
        if not watching_index:
            break  # All tracked tenders resolved; stop early

        check_date = today - timedelta(days=days_back)
        try:
            resp = session.get(
                f'{BASE_URL}/prkms/tender/common/noticeDate/readPublish',
                params={'dateStr': _to_roc_date(check_date)},
                headers=_HEADERS,
                timeout=60,
            )
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            _, awards = _parse_readpublish(soup, check_date)

            for award in awards:
                key = (_norm(award['unit']), _norm(award['name']))
                if key not in watching_index:
                    continue

                tender = watching_index.pop(key)
                time.sleep(_DELAY)  # be polite before the detail fetch
                detail = _get_bdm_detail(award['bdm_id'], award['award_date'], session)

                sheets.update_award(tender['_row_index'], {
                    'award_date':   detail.get('award_date',  award['award_date']),
                    'award_price':  detail.get('award_price', ''),
                    'award_vendor': detail.get('award_vendor', ''),
                })
                updated += 1
                print(f'[check_awards] awarded: {award["unit"]} / {award["name"][:40]}')

        except Exception as e:
            print(f'[check_awards] error on {check_date}: {e}')

        time.sleep(_DELAY)

    return updated


def debug_parse(target_date: date | None = None) -> None:
    """
    Print what the parser sees for a given date.
    Run locally to verify HTML structure before pushing.

      python -c "import crawler; from datetime import date; crawler.debug_parse(date(2026,1,2))"
    """
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
    tenders, awards = _parse_readpublish(soup, target_date)
    print(f'[debug] {target_date}: {len(tenders)} tenders, {len(awards)} awards')
    for a in awards[:10]:
        print(f'  BDM {a["bdm_id"]}: {a["unit"]} / {a["name"][:40]}')
