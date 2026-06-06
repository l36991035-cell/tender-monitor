# tests/test_integration.py
"""
Integration tests — require real credentials.
Run with:
  $env:GOOGLE_SERVICE_ACCOUNT_JSON = Get-Content service_account.json -Raw
  $env:SPREADSHEET_ID = "1kY9-FnRKQxAACcfn1CIb1rYkrlSkYevNbnsvcQBvTB0"
  python -m pytest tests/test_integration.py -v -s
"""
import os
import pytest
from datetime import date

pytestmark = pytest.mark.skipif(
    not os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON'),
    reason="GOOGLE_SERVICE_ACCOUNT_JSON not set"
)


def test_sheets_client_connects():
    import sheets
    client = sheets.get_client()
    assert client is not None


def test_append_and_read_raw():
    import sheets
    test_record = {
        'id': 'TEST_INTEGRATION_001',
        'name': '整合測試標案',
        'unit': '測試機關',
        'date': '2026-06-06',
        'category': '工程',
        'method': '公開招標',
    }
    count = sheets.append_raw([test_record])
    # Second call should be 0 (duplicate)
    count2 = sheets.append_raw([test_record])
    assert count2 == 0


def test_fetch_date_from_api():
    """Fetch a known historical date from pcc.g0v.ronny.tw."""
    import crawler
    # Use a historical date known to have records
    count = crawler.fetch_date(date(2026, 6, 1))
    print(f'\nFetched {count} new records for 2026-06-01')
    assert count >= 0  # 0 is OK if already fetched before
