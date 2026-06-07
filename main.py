# main.py
import argparse
import os
import sys

import crawler
import sheets
import notify


def run_daily():
    line_token = os.environ.get('LINE_NOTIFY_TOKEN', '')

    print('[1/3] Fetching today\'s tenders...')
    new_records = crawler.fetch_today_new()
    print(f'      → {len(new_records)} new records written to raw')

    if new_records:
        keywords = sheets.get_keywords()
        if keywords:
            matches = notify.match_keywords(new_records, keywords)
            print(f'      → {len(matches)} keyword matches ({", ".join(keywords[:5])})')
            notify.notify_new_tenders(line_token, matches)
        else:
            print('      → no active keywords set')

    print('[2/3] Checking awards for tracked tenders...')
    awarded = crawler.check_awards()
    print(f'      → {len(awarded)} tenders updated to awarded')
    notify.notify_awards(line_token, awarded)

    print('[3/3] Cleaning up raw sheet (>90 days)...')
    deleted = sheets.cleanup_raw(days=90)
    print(f'      → {deleted} old records deleted')


def run_backfill(days: int):
    print(f'[backfill] Fetching past {days} days...')
    count = crawler.fetch_backfill(days)
    print(f'           → {count} total new records written')


def main():
    parser = argparse.ArgumentParser(description='Government tender crawler')
    parser.add_argument('--backfill', type=int, default=0,
                        help='Fetch past N days instead of running daily job')
    args = parser.parse_args()

    try:
        if args.backfill > 0:
            run_backfill(args.backfill)
        else:
            run_daily()
    except Exception as e:
        print(f'[FATAL] {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
