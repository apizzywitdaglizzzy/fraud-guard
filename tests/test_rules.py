from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_create_and_list_rules(test_app, auth_headers):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a rule
        rule = {
            "name": "Test block high amount",
            "field": "amount",
            "operator": "gt",
            "value": 999999,
            "action": "block",
            "priority": 99,
        }
        resp = await client.post("/v1/rules", json=rule, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Test block high amount"
        rule_id = data["id"]

        # List rules
        resp = await client.get("/v1/rules", headers=auth_headers)
        assert resp.status_code == 200
        rules = resp.json()
        assert any(r["id"] == rule_id for r in rules)

        # Update rule
        resp = await client.put(f"/v1/rules/{rule_id}", json={"priority": 50}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["priority"] == 50

        # Delete rule
        resp = await client.delete(f"/v1/rules/{rule_id}", headers=auth_headers)
        assert resp.status_code == 204


@pytest.mark.asyncio
async def test_rule_triggers_on_screen(test_app, auth_headers):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a rule that blocks a specific BIN
        rule = {
            "name": "Block test BIN 666666",
            "field": "bin",
            "operator": "eq",
            "value": "666666",
            "action": "block",
            "priority": 100,
        }
        resp = await client.post("/v1/rules", json=rule, headers=auth_headers)
        assert resp.status_code == 201
        rule_id = resp.json()["id"]

        # Screen with that BIN
        payload = {
            "card_bin": "666666",
            "card_last4": "0001",
            "card_exp_month": 1,
            "card_exp_year": 2027,
            "amount": 500,
            "currency": "usd",
            "customer_ip": "1.2.3.4",
        }
        resp = await client.post("/v1/screen", json=payload, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] == "block"
        assert "Block test BIN 666666" in data["rules_triggered"]

        # Cleanup
        await client.delete(f"/v1/rules/{rule_id}", headers=auth_headers)
