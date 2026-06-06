# main.py
import argparse
import sys

import crawler
import sheets


def run_daily():
    print('[1/3] Fetching today\'s tenders...')
    count = crawler.fetch_today()
    print(f'      → {count} new records written to raw')

    print('[2/3] Checking awards for tracked tenders...')
    updated = crawler.check_awards()
    print(f'      → {updated} tenders updated to awarded')

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
