"""
Unit tests for scripts/bootstrap_admin.py.
"""

from unittest.mock import MagicMock, patch
import os
import pytest

from scripts.bootstrap_admin import bootstrap_admin


def test_bootstrap_admin_missing_env_vars(monkeypatch, capsys):
    monkeypatch.delenv("BOOTSTRAP_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)

    exit_code = bootstrap_admin()
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "[ERROR] Missing required environment variables:" in captured.out
    assert "BOOTSTRAP_ADMIN_EMAIL is not set" in captured.out
    assert "BOOTSTRAP_ADMIN_PASSWORD is not set" in captured.out


def test_bootstrap_admin_idempotent_existing_admin(monkeypatch, capsys):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "newadmin@helios.local")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "SuperSecret123!")

    mock_cursor = MagicMock()
    # Mock finding an existing admin (count = 1)
    mock_cursor.fetchone.return_value = (1,)

    with patch("scripts.bootstrap_admin.databricks_cursor") as mock_cursor_ctx:
        mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor
        exit_code = bootstrap_admin()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "An administrator already exists" in captured.out
    assert "No changes made" in captured.out
    assert "SuperSecret123!" not in captured.out

    # Assert no INSERT query was executed
    for call in mock_cursor.execute.call_args_list:
        query = call[0][0].lower()
        assert "insert into" not in query


def test_bootstrap_admin_creates_first_admin(monkeypatch, capsys):
    monkeypatch.setenv("BOOTSTRAP_ADMIN_EMAIL", "firstadmin@helios.local")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "SuperSecret123!")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_NAME", "Helios System Admin")

    mock_cursor = MagicMock()
    # 1st fetchone: admin count = 0
    # 2nd fetchone: existing email count = 0
    mock_cursor.fetchone.side_effect = [(0,), (0,)]

    with patch("scripts.bootstrap_admin.databricks_cursor") as mock_cursor_ctx, \
         patch("scripts.bootstrap_admin.get_password_hash", return_value="mock_hashed_pw") as mock_hash:
        mock_cursor_ctx.return_value.__enter__.return_value = mock_cursor
        exit_code = bootstrap_admin()

    assert exit_code == 0
    mock_hash.assert_called_once_with("SuperSecret123!")

    # Verify INSERT query execution
    executed_queries = [call[0] for call in mock_cursor.execute.call_args_list]
    insert_call = [q for q in executed_queries if "insert into" in q[0].lower()][0]
    sql, params = insert_call

    assert "platform`.`users`" in sql
    assert params["name"] == "Helios System Admin"
    assert params["email"] == "firstadmin@helios.local"
    assert params["password_hash"] == "mock_hashed_pw"

    captured = capsys.readouterr()
    assert "[SUCCESS] Initial Admin user successfully created with email: firstadmin@helios.local" in captured.out
    # Guarantee password is never logged
    assert "SuperSecret123!" not in captured.out
