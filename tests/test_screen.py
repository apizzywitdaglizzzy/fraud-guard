from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_screen_requires_auth(test_app, sample_screen_request):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/screen", json=sample_screen_request)
        assert resp.status_code == 422 or resp.status_code == 401


@pytest.mark.asyncio
async def test_screen_approve_legitimate(test_app, auth_headers, sample_screen_request):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/screen", json=sample_screen_request, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "approve"
        assert data["risk_score"] >= 0
        assert data["transaction_id"].startswith("txn_")
        assert "velocity" in data


@pytest.mark.asyncio
async def test_screen_velocity_detection(test_app, auth_headers):
    """Rapid-fire requests from same IP should eventually get blocked."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First, create a velocity rule
        rule = {
            "name": "Test velocity block",
            "field": "velocity_ip_1m",
            "operator": "gt",
            "value": 10,
            "action": "block",
            "priority": 100,
        }
        resp = await client.post("/v1/rules", json=rule, headers=auth_headers)
        assert resp.status_code == 201
        rule_id = resp.json()["id"]

        decisions = []
        for i in range(15):
            payload = {
                "card_bin": str(400000 + i),
                "card_last4": str(1000 + i),
                "card_exp_month": 6,
                "card_exp_year": 2026,
                "amount": 1000,
                "currency": "usd",
                "customer_ip": "10.0.0.99",  # same IP
            }
            resp = await client.post("/v1/screen", json=payload, headers=auth_headers)
            assert resp.status_code == 200
            decisions.append(resp.json()["decision"])

        # First few should approve, later ones should block
        assert "approve" in decisions
        assert "block" in decisions
        first_block = decisions.index("block")
        assert first_block > 0

        # Cleanup
        await client.delete(f"/v1/rules/{rule_id}", headers=auth_headers)


@pytest.mark.asyncio
async def test_screen_high_amount_signal(test_app, auth_headers):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "card_bin": "555555",
            "card_last4": "9999",
            "card_exp_month": 3,
            "card_exp_year": 2027,
            "amount": 100000,  # $1000
            "currency": "usd",
            "customer_ip": "192.168.50.1",
        }
        resp = await client.post("/v1/screen", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        signal_names = [s["name"] for s in data["signals"]]
        assert "high_amount" in signal_names


@pytest.mark.asyncio
async def test_dashboard_summary(test_app, auth_headers):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_screened" in data
        assert data["total_screened"] > 0


@pytest.mark.asyncio
async def test_dashboard_html(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/dashboard")
        assert resp.status_code == 200
        assert "FraudGuard" in resp.text
        assert "Total Screened" in resp.text
