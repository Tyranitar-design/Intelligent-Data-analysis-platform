# -*- coding: utf-8 -*-
"""Smoke Center 后端 contracts 测试"""
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from api.main import app  # noqa: E402


def test_smoke_scenarios_endpoint_contract():
    client = TestClient(app)

    response = client.get("/api/v1/smoke/scenarios")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["scenarios"], list)
    assert len(payload["scenarios"]) >= 3

    scenario_ids = {item["scenario_id"] for item in payload["scenarios"]}
    assert "local-upload-basic" in scenario_ids
    assert "live-public-static" in scenario_ids
    assert "live-assisted-bilibili" in scenario_ids

    local_scenario = next(item for item in payload["scenarios"] if item["scenario_id"] == "local-upload-basic")
    assert local_scenario["mode"] == "local"
    assert local_scenario["requires_robots_check"] is False
    assert local_scenario["requires_human"] is False

    assisted_scenario = next(item for item in payload["scenarios"] if item["scenario_id"] == "live-assisted-bilibili")
    assert assisted_scenario["mode"] == "live-assisted"
    assert assisted_scenario["requires_auth"] is True
    assert assisted_scenario["requires_human"] is True
    assert assisted_scenario["platform"] == "bilibili"


def test_smoke_contracts_endpoint_vocabulary():
    client = TestClient(app)

    response = client.get("/api/v1/smoke/contracts")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert "run_statuses" in payload
    assert "run_stages" in payload
    assert "assisted_auth_states" in payload

    assert payload["run_statuses"] == [
        "passed",
        "failed",
        "blocked_by_robots",
        "manual_checkpoint_required",
        "skipped",
    ]

    assert "waiting_for_human" in payload["assisted_auth_states"]
    assert "session_reuse_check" in payload["assisted_auth_states"]


if __name__ == "__main__":
    print("=== Testing Smoke Contracts ===")
    test_smoke_scenarios_endpoint_contract()
    print("[OK] Smoke scenarios contract verified")
    test_smoke_contracts_endpoint_vocabulary()
    print("[OK] Smoke contracts vocabulary verified")
    print("=== Smoke contracts tests passed ===")
