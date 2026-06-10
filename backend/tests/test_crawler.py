# tests/test_crawler.py
import pytest
from unittest.mock import patch, MagicMock, ANY
from datetime import date

SAMPLE_HTML = '''<html><body>
<a id="公開招標公告"><div class="font_title">□公開招標公告□</div></a>
<table class="tenderCase">
  <tr><td><a class="tenderLinkPublish" href="TIQ-1-71033172.xml">&lt;1&gt; 國立成功大學醫學院附設醫院：Y11536 - 大腸癌檢體甲基化基因次世代定序分析服務</a></td></tr>
  <tr><td class="summary">[是否屬特殊採購]否</td></tr>
</table>
<a id="限制性招標公告"><div class="font_title">□限制性招標公告□</div></a>
<table class="tenderCase">
  <tr><td><a class="tenderLinkPublish" href="TIQ-1-71036508.xml">&lt;2&gt; 教育部：LP-11511-001 - 辦公用品採購</a></td></tr>
  <tr><td class="summary">[是否屬特殊採購]否</td></tr>
</table>
</body></html>'''


def _make_html_response(html=SAMPLE_HTML):
    mock = MagicMock()
    mock.text = html
    mock.raise_for_status.return_value = None
    mock.encoding = 'utf-8'
    return mock


def test_to_roc_date():
    import crawler
    assert crawler._to_roc_date(date(2026, 6, 5)) == '115年06月05日'
    assert crawler._to_roc_date(date(2026, 1, 1)) == '115年01月01日'
    assert crawler._to_roc_date(date(2025, 12, 31)) == '114年12月31日'


def test_fetch_date_calls_correct_url():
    with patch('requests.get', return_value=_make_html_response()) as mock_get, \
         patch('crawler.sheets') as mock_sheets:
        mock_sheets.append_raw.return_value = [{}, {}]

        import crawler
        crawler.fetch_date(date(2026, 6, 5))

    mock_get.assert_called_once_with(
        'https://web.pcc.gov.tw/prkms/tender/common/noticeDate/readPublish',
        params={'dateStr': '115年06月05日'},
        headers=ANY,
        timeout=60,
    )


def test_fetch_date_maps_fields_correctly():
    with patch('requests.get', return_value=_make_html_response()), \
         patch('crawler.sheets') as mock_sheets:
        mock_sheets.append_raw.return_value = []

        import crawler
        crawler.fetch_date(date(2026, 6, 5))

    appended = mock_sheets.append_raw.call_args[0][0]
    assert len(appended) == 2

    first = appended[0]
    assert first['id'] == 'TIQ-1-71033172'
    assert first['name'] == '大腸癌檢體甲基化基因次世代定序分析服務'
    assert first['unit'] == '國立成功大學醫學院附設醫院'
    assert first['date'] == '2026-06-05'
    assert first['method'] == '公開招標公告'
    assert first['category'] == ''

    second = appended[1]
    assert second['id'] == 'TIQ-1-71036508'
    assert second['unit'] == '教育部'
    assert second['name'] == '辦公用品採購'
    assert second['method'] == '限制性招標公告'


def test_fetch_date_handles_empty_html():
    with patch('requests.get', return_value=_make_html_response('<html><body></body></html>')), \
         patch('crawler.sheets') as mock_sheets:
        mock_sheets.append_raw.return_value = []

        import crawler
        count = crawler.fetch_date(date(2026, 6, 5))

    assert count == 0


def test_fetch_date_returns_count_from_append_raw():
    with patch('requests.get', return_value=_make_html_response()), \
         patch('crawler.sheets') as mock_sheets:
        mock_sheets.append_raw.return_value = [{}]  # only 1 new (1 duplicate)

        import crawler
        count = crawler.fetch_date(date(2026, 6, 5))

    assert count == 1


def test_check_awards_no_matches():
    tracking = [
        {'id': 'TIQ-1-001', '_row_index': 2, 'unit': '某機關', 'name': '採購案A', 'status': 'tracking'},
        {'id': 'TIQ-1-002', '_row_index': 3, 'unit': '另一機關', 'name': '採購案B', 'status': 'tracking'},
    ]
    empty_html = _make_html_response('<html><body></body></html>')
    with patch('crawler.sheets') as mock_sheets, \
         patch('requests.Session') as mock_session_cls, \
         patch('time.sleep'):
        mock_session_cls.return_value.get.return_value = empty_html
        mock_sheets.get_watching_tracking.return_value = tracking

        import crawler
        updated = crawler.check_awards(lookback_days=1)

    assert updated == []
    mock_sheets.update_award.assert_not_called()


def test_check_awards_continues_on_error():
    tracking = [
        {'id': 'TIQ-1-A', '_row_index': 2, 'unit': '某機關', 'name': '採購案A', 'status': 'tracking'},
        {'id': 'TIQ-1-B', '_row_index': 3, 'unit': '另一機關', 'name': '採購案B', 'status': 'tracking'},
    ]
    with patch('crawler.sheets') as mock_sheets, \
         patch('requests.Session') as mock_session_cls, \
         patch('time.sleep'):
        mock_session_cls.return_value.get.side_effect = Exception('network error')
        mock_sheets.get_watching_tracking.return_value = tracking

        import crawler
        updated = crawler.check_awards(lookback_days=1)

    assert updated == []
