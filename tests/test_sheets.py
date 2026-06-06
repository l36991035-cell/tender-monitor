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
         patch("google.oauth2.service_account.Credentials.from_service_account_info") as mock_creds:
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
