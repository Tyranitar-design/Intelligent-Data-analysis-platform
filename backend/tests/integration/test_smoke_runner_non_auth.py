# -*- coding: utf-8 -*-
"""Smoke Center 非登录态 runner 测试"""
import os
import sys
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from api.main import app  # noqa: E402


def test_local_smoke_run_contract():
    client = TestClient(app)

    payload = {
        "scenario_id": "local-upload-basic",
        "dataset_name": "smoke_local_contract",
        "dataset_description": "local smoke contract test",
        "rows": [
            {"date": "2026-05-10", "value": 12.5, "category": "A"},
            {"date": "2026-05-11", "value": 18.0, "category": "B"},
        ],
    }

    response = client.post("/api/v1/smoke/run", json=payload)
    assert response.status_code == 200

    result = response.json()
    assert result["success"] is True
    assert result["scenario_id"] == "local-upload-basic"
    assert result["status"] == "passed"
    assert result["stage"] == "completed"
    assert result["requires_human"] is False
    assert result["dataset_saved"] is True
    assert result["analysis_passed"] is True
    assert result["report_passed"] is True
    assert result["crawl_strategy"] == "local"
    assert result["robots"]["checked"] is False
    assert result["artifacts"]["dataset"]["table_name"]


def test_live_public_static_blocked_by_robots_contract():
    client = TestClient(app)

    with patch("api.routers.smoke.execute_non_auth_smoke_run") as mocked_run:
        mocked_run.return_value = {
            "success": True,
            "scenario_id": "live-public-static",
            "status": "blocked_by_robots",
            "stage": "robots_check",
            "requires_human": False,
            "dataset_saved": False,
            "analysis_passed": False,
            "report_passed": False,
            "crawl_strategy": "url/crawl",
            "robots": {
                "checked": True,
                "allowed": False,
                "source": "robots.txt",
            },
            "artifacts": {},
            "notes": ["Target disallowed by robots.txt"],
            "error": None,
        }

        response = client.post("/api/v1/smoke/run", json={
            "scenario_id": "live-public-static",
            "url": "https://example.com/protected",
        })

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "blocked_by_robots"
    assert result["stage"] == "robots_check"
    assert result["dataset_saved"] is False
    assert result["analysis_passed"] is False
    assert result["report_passed"] is False
    assert result["robots"]["allowed"] is False


def test_local_smoke_run_records_memory_capture_metadata():
    client = TestClient(app)

    payload = {
        "scenario_id": "local-upload-basic",
        "dataset_name": "smoke_local_memory",
        "dataset_description": "local smoke memory capture test",
        "rows": [
            {"date": "2026-05-10", "value": 21.0, "category": "A"},
            {"date": "2026-05-11", "value": 34.5, "category": "B"},
        ],
    }

    with patch("smoke.service.record_smoke_memory_capture") as mocked_capture:
        mocked_capture.return_value = {
            "captured": True,
            "capture_path": "C:/memory/captures/local-smoke.md",
            "synced": True,
            "sync_path": "C:/memory/index/memory.sqlite",
            "error": None,
        }

        response = client.post("/api/v1/smoke/run", json=payload)

    assert response.status_code == 200
    result = response.json()
    assert result["memory_capture"]["captured"] is True
    assert result["memory_capture"]["synced"] is True
    assert result["memory_capture"]["capture_path"].endswith("local-smoke.md")
    mocked_capture.assert_called_once()


if __name__ == "__main__":
    print("=== Testing Smoke Runner (Non-Auth) ===")
    test_local_smoke_run_contract()
    print("[OK] Local smoke run contract verified")
    test_live_public_static_blocked_by_robots_contract()
    print("[OK] Live public robots-blocked contract verified")
    print("=== Smoke runner non-auth tests passed ===")
