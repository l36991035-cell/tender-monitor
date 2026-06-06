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


SAMPLE_DETAIL_AWARDED = {
    "detail": {
        "award": {
            "award_date": "2026-06-10",
            "award_price": "1500000",
            "award_vendor": "優良建設股份有限公司"
        }
    }
}

SAMPLE_DETAIL_NOT_AWARDED = {
    "detail": {
        "award": {}
    }
}


def test_get_award_info_returns_dict_when_awarded():
    """_get_award_info must return award fields when award_date is present."""
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_DETAIL_AWARDED
    mock_response.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_response) as mock_get:
        import crawler
        result = crawler._get_award_info('A04010000_112001')

    mock_get.assert_called_once_with(
        'https://pcc.g0v.ronny.tw/tender/detail',
        params={'unit_id': 'A04010000', 'job_number': '112001'},
        timeout=30
    )
    assert result == {
        'award_date': '2026-06-10',
        'award_price': '1500000',
        'award_vendor': '優良建設股份有限公司',
    }


def test_get_award_info_returns_none_when_not_awarded():
    """_get_award_info must return None when award_date is missing."""
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_DETAIL_NOT_AWARDED
    mock_response.raise_for_status.return_value = None

    with patch('requests.get', return_value=mock_response):
        import crawler
        result = crawler._get_award_info('B09010000_220005')

    assert result is None


def test_get_award_info_invalid_id_returns_none():
    """_get_award_info must return None when tender id has no underscore."""
    import crawler
    result = crawler._get_award_info('INVALIDID')
    assert result is None


def test_check_awards_updates_awarded_tenders():
    """check_awards must call update_award for each tender that now has award info."""
    tracking = [
        {'id': 'A_1', 'name': 'T1', '_row_index': 2, 'status': 'tracking'},
        {'id': 'B_2', 'name': 'T2', '_row_index': 3, 'status': 'tracking'},
    ]
    award_info = {'award_date': '2026-06-10', 'award_price': '100000', 'award_vendor': 'Corp'}

    with patch('crawler.sheets') as mock_sheets, \
         patch('crawler._get_award_info') as mock_award, \
         patch('time.sleep'):  # skip actual sleep
        mock_sheets.get_watching_tracking.return_value = tracking
        mock_award.side_effect = [award_info, None]  # A_1 awarded, B_2 not yet

        import crawler
        updated = crawler.check_awards()

    assert updated == 1
    mock_sheets.update_award.assert_called_once_with(2, award_info)


def test_check_awards_continues_on_error():
    """check_awards must not abort when a single tender check fails."""
    tracking = [
        {'id': 'A_1', '_row_index': 2, 'status': 'tracking'},
        {'id': 'B_2', '_row_index': 3, 'status': 'tracking'},
    ]

    with patch('crawler.sheets') as mock_sheets, \
         patch('crawler._get_award_info') as mock_award, \
         patch('time.sleep'):
        mock_sheets.get_watching_tracking.return_value = tracking
        mock_award.side_effect = [Exception("network error"),
                                   {'award_date': '2026-06-10', 'award_price': '50000', 'award_vendor': 'Y'}]

        import crawler
        updated = crawler.check_awards()

    assert updated == 1  # B_2 succeeded despite A_1 error
