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
