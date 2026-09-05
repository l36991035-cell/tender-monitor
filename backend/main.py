# main.py
import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from datetime import date

import crawler
import notify


def _load_keywords() -> list[str]:
    kw_path = os.environ.get('KEYWORDS_PATH', '')
    if not kw_path:
        return []
    try:
        with open(kw_path, encoding='utf-8') as f:
            data = json.load(f)
        return [str(k) for k in data if str(k).strip()]
    except Exception:
        return []


def _match_keywords(records: list[dict], keywords: list[str]) -> list[dict]:
    results = []
    seen: set[str] = set()
    for r in records:
        for kw in keywords:
            if kw in r.get('name', '') or kw in r.get('unit', ''):
                if r['id'] not in seen:
                    seen.add(r['id'])
                    results.append({**r, 'matched_keyword': kw})
                break
    return results


def _save_results(matches: list[dict]) -> None:
    output_path = os.environ.get('DASHBOARD_TENDER_PATH', '')
    if not output_path:
        print('[warn] DASHBOARD_TENDER_PATH not set, skipping save')
        return
    data = {
        'saved_at': datetime.now().isoformat(),
        'date': datetime.now().strftime('%Y-%m-%d'),
        'matches': matches,
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'      → {len(matches)} 筆結果已儲存')


def run_daily():
    date_override = os.environ.get('DATE_OVERRIDE', '')
    target_date = date.fromisoformat(date_override) if date_override else None
    label = date_override if date_override else '今天'
    print(f'[1/3] Fetching tenders for {label}...')
    tenders = crawler.fetch_today_new(target_date)
    print(f'      → {len(tenders)} 筆標案')

    keywords = _load_keywords()
    if keywords:
        matches = _match_keywords(tenders, keywords)
        print(f'      → {len(matches)} 筆符合關鍵字（{", ".join(keywords)}）')
    else:
        matches = []
        print('      → 無關鍵字設定')

    print('[2/2] Saving results...')
    _save_results(matches)

    print('[3/3] Sending email notification...')
    notify.notify_new_tenders(matches)


def main():
    try:
        run_daily()
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        print(f'[FATAL] {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
