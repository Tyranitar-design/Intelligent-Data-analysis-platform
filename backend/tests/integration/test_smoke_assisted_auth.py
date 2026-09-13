# -*- coding: utf-8 -*-
"""Smoke Center assisted-auth contract tests"""
import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from api.main import app  # noqa: E402


def test_assisted_auth_start_contract():
    client = TestClient(app)

    response = client.post("/api/v1/smoke/assisted/start", json={
        "scenario_id": "live-assisted-bilibili",
        "url": "https://www.bilibili.com",
    })
    assert response.status_code == 200

    result = response.json()
    assert result["success"] is True
    assert result["scenario_id"] == "live-assisted-bilibili"
    assert result["status"] == "manual_checkpoint_required"
    assert result["stage"] == "waiting_for_human"
    assert result["requires_human"] is True
    assert result["assisted_auth_state"] == "waiting_for_human"
    assert result["platform"] == "bilibili"
    assert result["continuation_token"]
    assert "login_url" in result["artifacts"]


def test_assisted_auth_continue_contract():
    client = TestClient(app)

    start_response = client.post("/api/v1/smoke/assisted/start", json={
        "scenario_id": "live-assisted-bilibili",
        "url": "https://www.bilibili.com",
    })
    token = start_response.json()["continuation_token"]

    continue_response = client.post("/api/v1/smoke/assisted/continue", json={
        "continuation_token": token,
    })
    assert continue_response.status_code == 200

    result = continue_response.json()
    assert result["success"] is True
    assert result["status"] in ["completed", "failed"]
    assert result["stage"] == "session_reuse_check"
    assert result["requires_human"] is True
    assert result["assisted_auth_state"] in ["session_reuse_check", "failed"]


def test_assisted_auth_start_records_memory_capture_metadata():
    client = TestClient(app)

    with patch("smoke.assisted_auth.record_smoke_memory_capture") as mocked_capture:
        mocked_capture.return_value = {
            "captured": True,
            "capture_path": "C:/memory/captures/assisted-start.md",
            "synced": True,
            "sync_path": "C:/memory/index/memory.sqlite",
            "error": None,
        }

        response = client.post("/api/v1/smoke/assisted/start", json={
            "scenario_id": "live-assisted-bilibili",
            "url": "https://www.bilibili.com",
        })

    assert response.status_code == 200
    result = response.json()
    assert result["memory_capture"]["captured"] is True
    assert result["memory_capture"]["capture_path"].endswith("assisted-start.md")
    mocked_capture.assert_called_once()


if __name__ == "__main__":
    print("=== Testing Smoke Assisted Auth Contracts ===")
    test_assisted_auth_start_contract()
    print("[OK] Assisted-auth start contract verified")
    test_assisted_auth_continue_contract()
    print("[OK] Assisted-auth continue contract verified")
    print("=== Smoke assisted-auth tests passed ===")
