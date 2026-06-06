# tests/test_sheets.py
import os
import json
import pytest
from unittest.mock import patch, MagicMock


def test_get_client_reads_env_var(monkeypatch):
    """get_client() must construct gspread client from GOOGLE_SERVICE_ACCOUNT_JSON env var."""
    fake_info = {
        "type": "service_account",
        "project_id": "test",
        "private_key_id": "key123",
        "private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA0Z3VS5JJcds3xHn/ygWep4gEMZBna7iGf79YLXY=\n-----END RSA PRIVATE KEY-----\n",
        "client_email": "test@test.iam.gserviceaccount.com",
        "client_id": "123",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", json.dumps(fake_info))
    monkeypatch.setenv("SPREADSHEET_ID", "sheet123")

    with patch("gspread.authorize") as mock_auth, \
         patch("sheets.Credentials.from_service_account_info") as mock_creds:
        mock_creds.return_value = MagicMock()
        mock_auth.return_value = MagicMock()

        import sheets
        client = sheets.get_client()

        mock_creds.assert_called_once()
        call_args = mock_creds.call_args
        assert call_args[0][0]["client_email"] == "test@test.iam.gserviceaccount.com"
        assert client is not None


def test_get_client_raises_on_missing_env(monkeypatch):
    """get_client() must raise KeyError when env var is missing."""
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)

    import importlib
    import sheets
    importlib.reload(sheets)

    with pytest.raises(KeyError):
        sheets.get_client()


def _make_ws_mock(existing_values=None):
    """Helper: returns a worksheet mock with get_all_values pre-configured."""
    ws = MagicMock()
    if existing_values is None:
        existing_values = [['id', 'name', 'unit', 'date', 'category', 'method', 'fetched_at']]
    ws.get_all_values.return_value = existing_values
    return ws


def test_append_raw_writes_new_records(monkeypatch):
    """append_raw must batch-append records that aren't already in the sheet."""
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("SPREADSHEET_ID", "sheet123")

    ws = _make_ws_mock()  # empty sheet (header only)

    import sheets
    with patch.object(sheets, '_get_sheet', return_value=ws):
        records = [
            {'id': 'A001_JOB1', 'name': 'Test Tender', 'unit': 'Agency A',
             'date': '2026-06-06', 'category': '工程', 'method': '公開招標'},
        ]
        count = sheets.append_raw(records)

    assert count == 1
    ws.append_rows.assert_called_once()
    appended = ws.append_rows.call_args[0][0]
    assert len(appended) == 1
    assert appended[0][0] == 'A001_JOB1'


def test_append_raw_skips_duplicates(monkeypatch):
    """append_raw must skip records whose id already exists in the sheet."""
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("SPREADSHEET_ID", "sheet123")

    existing = [
        ['id', 'name', 'unit', 'date', 'category', 'method', 'fetched_at'],
        ['A001_JOB1', 'Test Tender', 'Agency A', '2026-06-05', '工程', '公開招標', '2026-06-05T08:00:00'],
    ]
    ws = _make_ws_mock(existing)

    import sheets
    with patch.object(sheets, '_get_sheet', return_value=ws):
        records = [
            {'id': 'A001_JOB1', 'name': 'Test Tender', 'unit': 'Agency A',
             'date': '2026-06-06', 'category': '工程', 'method': '公開招標'},
            {'id': 'A002_JOB2', 'name': 'New Tender', 'unit': 'Agency B',
             'date': '2026-06-06', 'category': '財物', 'method': '公開招標'},
        ]
        count = sheets.append_raw(records)

    assert count == 1  # only A002_JOB2 is new
    appended = ws.append_rows.call_args[0][0]
    assert appended[0][0] == 'A002_JOB2'


def test_append_raw_empty_sheet(monkeypatch):
    """append_raw must handle a truly empty sheet (no header row yet) gracefully."""
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("SPREADSHEET_ID", "sheet123")

    ws = _make_ws_mock(existing_values=[])  # completely empty

    import sheets
    with patch.object(sheets, '_get_sheet', return_value=ws):
        count = sheets.append_raw([
            {'id': 'X_Y', 'name': 'N', 'unit': 'U', 'date': '2026-06-06',
             'category': '工程', 'method': '公開'}
        ])

    assert count == 1


def test_get_watching_tracking_returns_only_tracking(monkeypatch):
    """get_watching_tracking must return only rows where status == 'tracking', with _row_index."""
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("SPREADSHEET_ID", "sheet123")

    ws = MagicMock()
    ws.get_all_records.return_value = [
        {'id': 'A_1', 'name': 'Tender 1', 'unit': 'U1', 'date': '2026-06-01',
         'category': '工程', 'added_at': '2026-06-01', 'status': 'tracking',
         'award_date': '', 'award_price': '', 'award_vendor': '', 'last_checked': ''},
        {'id': 'B_2', 'name': 'Tender 2', 'unit': 'U2', 'date': '2026-06-02',
         'category': '財物', 'added_at': '2026-06-02', 'status': 'awarded',
         'award_date': '2026-06-03', 'award_price': '100000', 'award_vendor': 'Vendor X', 'last_checked': '2026-06-03'},
        {'id': 'C_3', 'name': 'Tender 3', 'unit': 'U3', 'date': '2026-06-03',
         'category': '勞務', 'added_at': '2026-06-03', 'status': 'tracking',
         'award_date': '', 'award_price': '', 'award_vendor': '', 'last_checked': ''},
    ]

    import sheets
    with patch.object(sheets, '_get_sheet', return_value=ws):
        result = sheets.get_watching_tracking()

    assert len(result) == 2
    assert result[0]['id'] == 'A_1'
    assert result[0]['_row_index'] == 2  # header is row 1, first data row is row 2
    assert result[1]['id'] == 'C_3'
    assert result[1]['_row_index'] == 4  # third data row (B_2 is row 3, C_3 is row 4)


def test_update_award_sets_fields_and_status(monkeypatch):
    """update_award must set award_date, award_price, award_vendor, status=awarded, last_checked."""
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("SPREADSHEET_ID", "sheet123")

    ws = MagicMock()

    import sheets
    with patch.object(sheets, '_get_sheet', return_value=ws):
        sheets.update_award(
            row_index=3,
            award_info={
                'award_date': '2026-06-05',
                'award_price': '500000',
                'award_vendor': 'Great Corp',
            }
        )

    # watching cols: 1=id,2=name,3=unit,4=date,5=category,6=added_at,7=status,
    #                8=award_date,9=award_price,10=award_vendor,11=last_checked
    cell_updates = {(c.args[0], c.args[1]): c.args[2] for c in ws.update_cell.call_args_list}
    assert cell_updates[(3, 7)] == 'awarded'       # status col
    assert cell_updates[(3, 8)] == '2026-06-05'    # award_date col
    assert cell_updates[(3, 9)] == '500000'        # award_price col
    assert cell_updates[(3, 10)] == 'Great Corp'   # award_vendor col
    assert (3, 11) in cell_updates                 # last_checked col (value is a timestamp)


def test_cleanup_raw_deletes_old_rows(monkeypatch):
    """cleanup_raw must delete rows older than N days, but preserve watching ids."""
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("SPREADSHEET_ID", "sheet123")

    raw_ws = MagicMock()
    raw_ws.get_all_values.return_value = [
        ['id', 'name', 'unit', 'date', 'category', 'method', 'fetched_at'],
        ['OLD_1', 'Old Tender', 'U1', '2025-01-01', '工程', '公開', '2025-01-01T08:00:00'],  # old, not watching
        ['OLD_2', 'Watched Old', 'U2', '2025-01-02', '財物', '公開', '2025-01-02T08:00:00'],  # old but in watching
        ['NEW_1', 'New Tender', 'U3', '2026-06-05', '勞務', '公開', '2026-06-05T08:00:00'],  # new, keep
    ]

    watching_ws = MagicMock()
    watching_ws.get_all_records.return_value = [
        {'id': 'OLD_2', 'status': 'tracking'},
    ]

    def mock_get_sheet(name):
        return raw_ws if name == 'raw' else watching_ws

    import sheets
    with patch.object(sheets, '_get_sheet', side_effect=mock_get_sheet):
        deleted = sheets.cleanup_raw(days=90)

    assert deleted == 1  # only OLD_1 deleted; OLD_2 protected; NEW_1 kept
    raw_ws.delete_rows.assert_called_once_with(2)  # OLD_1 is row 2 (1-based, header=row1)


def test_cleanup_raw_no_deletions(monkeypatch):
    """cleanup_raw returns 0 when all rows are recent."""
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("SPREADSHEET_ID", "sheet123")

    raw_ws = MagicMock()
    raw_ws.get_all_values.return_value = [
        ['id', 'name', 'unit', 'date', 'category', 'method', 'fetched_at'],
        ['X_1', 'Tender', 'U1', '2026-06-05', '工程', '公開', '2026-06-05T08:00:00'],
    ]

    watching_ws = MagicMock()
    watching_ws.get_all_records.return_value = []

    def mock_get_sheet(name):
        return raw_ws if name == 'raw' else watching_ws

    import sheets
    with patch.object(sheets, '_get_sheet', side_effect=mock_get_sheet):
        deleted = sheets.cleanup_raw(days=90)

    assert deleted == 0
    raw_ws.delete_rows.assert_not_called()


def test_get_keywords_returns_active_only(monkeypatch):
    """get_keywords must return only keywords where active == 'TRUE' (case-insensitive)."""
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", "{}")
    monkeypatch.setenv("SPREADSHEET_ID", "sheet123")

    ws = MagicMock()
    ws.get_all_records.return_value = [
        {'keyword': '污水', 'created_at': '2026-01-01', 'active': 'TRUE'},
        {'keyword': '道路', 'created_at': '2026-01-02', 'active': 'FALSE'},
        {'keyword': '橋梁', 'created_at': '2026-01-03', 'active': 'TRUE'},
        {'keyword': '停用', 'created_at': '2026-01-04', 'active': 'false'},
    ]

    import sheets
    with patch.object(sheets, '_get_sheet', return_value=ws):
        result = sheets.get_keywords()

    assert result == ['污水', '橋梁']
