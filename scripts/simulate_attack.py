"""Simulate a card testing attack to demo FraudGuard's velocity detection."""
from __future__ import annotations

import asyncio
import random
import sys
import time

import httpx

BASE_URL = "http://localhost:8000"
API_KEY = "fg_test_key_dev_12345"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def random_bin():
    return str(random.randint(400000, 499999))


def random_last4():
    return str(random.randint(1000, 9999))


async def screen(client: httpx.AsyncClient, ip: str, bin: str = None, email: str = None):
    payload = {
        "card_bin": bin or random_bin(),
        "card_last4": random_last4(),
        "card_exp_month": random.randint(1, 12),
        "card_exp_year": 2026,
        "amount": random.randint(100, 10000),
        "currency": "usd",
        "customer_ip": ip,
    }
    if email:
        payload["customer_email"] = email

    resp = await client.post(f"{BASE_URL}/v1/screen", json=payload, headers=HEADERS)
    data = resp.json()
    decision = data.get("decision", "error")
    score = data.get("risk_score", 0)
    signals = [s["name"] for s in data.get("signals", [])]
    rules = data.get("rules_triggered", [])
    return decision, score, signals, rules


async def run_card_testing_attack():
    """Simulate an attacker testing 50 stolen cards from the same IP."""
    print("=" * 60)
    print("SIMULATION: Card Testing Attack")
    print("50 different cards from the same IP in rapid succession")
    print("=" * 60)

    attacker_ip = "185.220.101.42"

    async with httpx.AsyncClient() as client:
        for i in range(50):
            decision, score, signals, rules = await screen(client, attacker_ip)
            status = {
                "approve": "\033[92mAPPROVE\033[0m",
                "flag": "\033[93mFLAG\033[0m",
                "block": "\033[91mBLOCK\033[0m",
            }.get(decision, decision)

            print(f"  #{i+1:>2}  {status}  score={score:.2f}  signals={signals}  rules={rules}")
            await asyncio.sleep(0.05)  # 50ms between requests

    print()


async def run_legitimate_traffic():
    """Simulate normal traffic — different IPs, low velocity."""
    print("=" * 60)
    print("SIMULATION: Legitimate Traffic")
    print("10 normal transactions from different IPs")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        for i in range(10):
            ip = f"73.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
            decision, score, signals, rules = await screen(
                client, ip,
                bin="411111",  # Visa test BIN
                email=f"user{i}@example.com",
            )
            status = {
                "approve": "\033[92mAPPROVE\033[0m",
                "flag": "\033[93mFLAG\033[0m",
                "block": "\033[91mBLOCK\033[0m",
            }.get(decision, decision)

            print(f"  #{i+1:>2}  {status}  score={score:.2f}  signals={signals}")
            await asyncio.sleep(0.2)

    print()


async def run_prepaid_card_test():
    """Simulate a transaction with a known prepaid BIN."""
    print("=" * 60)
    print("SIMULATION: Prepaid Card From High-Risk Country")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # Use a BIN that would resolve as prepaid (for demo, rules will catch it)
        decision, score, signals, rules = await screen(
            client, "197.210.54.12",
            bin="404010",  # known prepaid BIN
            email="test@tempmail.com",
        )
        status = {
            "approve": "\033[92mAPPROVE\033[0m",
            "flag": "\033[93mFLAG\033[0m",
            "block": "\033[91mBLOCK\033[0m",
        }.get(decision, decision)
        print(f"  Result: {status}  score={score:.2f}")
        print(f"  Signals: {signals}")
        print(f"  Rules: {rules}")

    print()


async def main():
    print("\n🛡️  FraudGuard Attack Simulator\n")

    # Check if server is running
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{BASE_URL}/health")
            if resp.status_code != 200:
                print("ERROR: FraudGuard server not responding. Start it with:")
                print("  cd fraudguard && uvicorn app.main:app --reload")
                return
        except httpx.ConnectError:
            print("ERROR: Cannot connect to FraudGuard. Start it with:")
            print("  cd fraudguard && uvicorn app.main:app --reload")
            return

    await run_legitimate_traffic()
    await run_card_testing_attack()
    await run_prepaid_card_test()

    # Show dashboard summary
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/v1/dashboard/summary", headers=HEADERS)
        print("=" * 60)
        print("DASHBOARD SUMMARY")
        print("=" * 60)
        data = resp.json()
        print(f"  Screened:  {data['total_screened']}")
        print(f"  Approved:  {data['total_approved']}")
        print(f"  Flagged:   {data['total_flagged']}")
        print(f"  Blocked:   {data['total_blocked']}")
        print(f"  Block Rate: {data['block_rate']:.1%}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
