"""Tests del endpoint /healthz y del legacy /health."""
import pytest


pytestmark = pytest.mark.asyncio


async def test_healthz_ok(client):
    r = await client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert "version" in body
    assert "uptime_seconds" in body
    assert isinstance(body["uptime_seconds"], int)
    assert body["environment"]


async def test_health_legacy_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "version" in body
