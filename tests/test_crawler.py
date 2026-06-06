# tests/test_crawler.py
import pytest
from unittest.mock import patch, MagicMock
from datetime import date


SAMPLE_API_RESPONSE = {
    "records": [
        {
            "id": "A04010000_112001",
            "name": "新建工程採購案",
            "unit": "台北市政府工務局",
            "date": "2026-06-06",
            "radard": "公開招標",
            "attr": "工程"
        },
        {
            "id": "B09010000_220005",
            "name": "辦公用品採購",
            "unit": "教育部",
            "date": "2026-06-06",
            "radard": "公開招標",
            "attr": "財物"
        }
    ]
}


def test_fetch_date_calls_correct_url():
    """fetch_date must GET /index/date/{date} and return count of written records."""
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_API_RESPONSE
    mock_response.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_response) as mock_get, \
         patch('crawler.sheets') as mock_sheets:
        mock_sheets.append_raw.return_value = 2

        import crawler
        count = crawler.fetch_date(date(2026, 6, 6))

    mock_get.assert_called_once_with(
        'https://pcc.g0v.ronny.tw/index/date/2026-06-06',
        timeout=30
    )
    assert count == 2


def test_fetch_date_maps_fields_correctly():
    """fetch_date must map API fields to the correct record dict keys."""
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_API_RESPONSE
    mock_response.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_response), \
         patch('crawler.sheets') as mock_sheets:
        mock_sheets.append_raw.return_value = 2

        import crawler
        crawler.fetch_date(date(2026, 6, 6))

    appended = mock_sheets.append_raw.call_args[0][0]
    assert len(appended) == 2
    first = appended[0]
    assert first['id'] == 'A04010000_112001'
    assert first['name'] == '新建工程採購案'
    assert first['unit'] == '台北市政府工務局'
    assert first['date'] == '2026-06-06'
    assert first['category'] == '工程'
    assert first['method'] == '公開招標'


def test_fetch_date_handles_empty_response():
    """fetch_date must handle API returning empty records list."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"records": []}
    mock_response.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_response), \
         patch('crawler.sheets') as mock_sheets:
        mock_sheets.append_raw.return_value = 0

        import crawler
        count = crawler.fetch_date(date(2026, 6, 6))

    assert count == 0
