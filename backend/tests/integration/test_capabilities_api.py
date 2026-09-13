# -*- coding: utf-8 -*-
"""测试系统能力状态 API"""
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from api.main import app  # noqa: E402


def test_capabilities_endpoint():
    client = TestClient(app)

    response = client.get("/capabilities")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert "service" in payload
    assert "version" in payload
    assert "capabilities" in payload
    assert "environment" in payload

    capabilities = payload["capabilities"]
    for key in ["auth", "crawl", "analysis", "data", "reports"]:
        assert key in capabilities
        assert capabilities[key]["enabled"] is True
        assert capabilities[key]["category"] == "core"

    for key in ["ml", "dl", "mining"]:
        assert key in capabilities
        assert capabilities[key]["category"] == "optional"
        assert isinstance(capabilities[key]["enabled"], bool)

    environment = payload["environment"]
    assert environment["database"]["configured"] is True
    assert "sqlite" in environment["database"]["driver"]
    assert environment["storage"]["configured"] is True
    assert environment["queue"]["configured"] is True


if __name__ == "__main__":
    print("=== Testing Capabilities API ===")
    test_capabilities_endpoint()
    print("[OK] /capabilities response structure verified")
    print("=== Capabilities API tests passed ===")
