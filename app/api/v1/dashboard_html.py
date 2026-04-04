from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.db.repository import Repository
from app.dependencies import get_repo

router = APIRouter()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FraudGuard Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e0e0e0; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { font-size: 24px; color: #fff; margin-bottom: 8px; }
        .subtitle { color: #666; font-size: 14px; margin-bottom: 30px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 30px; }
        .stat-card { background: #12121a; border: 1px solid #1e1e2e; border-radius: 12px; padding: 20px; }
        .stat-label { font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .stat-value { font-size: 32px; font-weight: 700; }
        .stat-value.green { color: #22c55e; }
        .stat-value.red { color: #ef4444; }
        .stat-value.yellow { color: #eab308; }
        .stat-value.blue { color: #3b82f6; }
        .stat-value.purple { color: #a855f7; }
        .section { background: #12121a; border: 1px solid #1e1e2e; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
        .section-title { font-size: 16px; font-weight: 600; margin-bottom: 16px; color: #fff; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th { text-align: left; padding: 10px 12px; color: #666; font-weight: 500; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; border-bottom: 1px solid #1e1e2e; }
        td { padding: 10px 12px; border-bottom: 1px solid #1a1a24; }
        .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
        .badge-approve { background: rgba(34,197,94,0.15); color: #22c55e; }
        .badge-block { background: rgba(239,68,68,0.15); color: #ef4444; }
        .badge-flag { background: rgba(234,179,8,0.15); color: #eab308; }
        .score-bar { width: 60px; height: 6px; background: #1e1e2e; border-radius: 3px; display: inline-block; vertical-align: middle; margin-right: 8px; }
        .score-fill { height: 100%; border-radius: 3px; }
        .risk-low .score-fill { background: #22c55e; }
        .risk-med .score-fill { background: #eab308; }
        .risk-high .score-fill { background: #ef4444; }
        .rules-tag { display: inline-block; padding: 2px 8px; margin: 2px; background: rgba(139,92,246,0.15); color: #a78bfa; border-radius: 4px; font-size: 11px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .logo { display: flex; align-items: center; gap: 12px; }
        .logo-icon { width: 36px; height: 36px; background: linear-gradient(135deg, #3b82f6, #a855f7); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
        .live-dot { width: 8px; height: 8px; background: #22c55e; border-radius: 50%; display: inline-block; animation: pulse 2s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        .refresh-btn { background: #1e1e2e; border: 1px solid #2e2e3e; color: #999; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; }
        .refresh-btn:hover { background: #2e2e3e; color: #fff; }
        .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        @media (max-width: 768px) { .two-col { grid-template-columns: 1fr; } }
        .empty { color: #444; text-align: center; padding: 40px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">
                <div class="logo-icon">&#x1f6e1;</div>
                <div>
                    <h1>FraudGuard</h1>
                    <div class="subtitle"><span class="live-dot"></span>&nbsp; Live Dashboard &mdash; Last 24 hours</div>
                </div>
            </div>
            <button class="refresh-btn" onclick="location.reload()">&#x21bb; Refresh</button>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Screened</div>
                <div class="stat-value blue">{{total_screened}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Approved</div>
                <div class="stat-value green">{{total_approved}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Blocked</div>
                <div class="stat-value red">{{total_blocked}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Flagged</div>
                <div class="stat-value yellow">{{total_flagged}}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Block Rate</div>
                <div class="stat-value purple">{{block_rate}}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Disputes</div>
                <div class="stat-value red">{{dispute_count}}</div>
            </div>
        </div>

        <div class="two-col">
            <div class="section">
                <div class="section-title">Recent Transactions</div>
                {{transactions_table}}
            </div>
            <div class="section">
                <div class="section-title">Top Risk BINs</div>
                {{bins_table}}
            </div>
        </div>

        <div class="section">
            <div class="section-title">Blocked Transactions</div>
            {{blocked_table}}
        </div>

        <div class="section">
            <div class="section-title">Active Rules</div>
            {{rules_table}}
        </div>
    </div>
</body>
</html>
"""


def _txn_table(rows: list[dict]) -> str:
    if not rows:
        return '<div class="empty">No transactions yet</div>'
    html = "<table><tr><th>Time</th><th>BIN</th><th>IP</th><th>Amount</th><th>Score</th><th>Decision</th><th>Rules</th></tr>"
    for r in rows[:20]:
        decision = r.get("decision", "")
        badge_class = f"badge-{decision}"
        score = r.get("risk_score", 0)
        risk_class = "risk-high" if score >= 0.5 else "risk-med" if score >= 0.2 else "risk-low"
        rules = json.loads(r.get("rules_triggered", "[]"))
        rules_html = "".join(f'<span class="rules-tag">{ru}</span>' for ru in rules) if rules else '<span style="color:#444">—</span>'
        amount = r.get("amount", 0) / 100
        ts = r.get("created_at", "")[:19].replace("T", " ")

        html += f"""<tr>
            <td style="color:#666">{ts}</td>
            <td>{r.get('card_bin','')}</td>
            <td>{r.get('customer_ip','')}</td>
            <td>${amount:.2f}</td>
            <td><span class="score-bar {risk_class}"><span class="score-fill" style="width:{score*100}%"></span></span>{score:.2f}</td>
            <td><span class="badge {badge_class}">{decision.upper()}</span></td>
            <td>{rules_html}</td>
        </tr>"""
    html += "</table>"
    return html


def _bins_table(rows: list[dict]) -> str:
    if not rows:
        return '<div class="empty">No BIN data yet</div>'
    html = "<table><tr><th>BIN</th><th>Screens</th><th>Blocks</th><th>Disputes</th><th>Risk Ratio</th></tr>"
    for r in rows:
        ratio = r.get("risk_ratio", 0)
        color = "#ef4444" if ratio > 0.3 else "#eab308" if ratio > 0.1 else "#22c55e"
        html += f"""<tr>
            <td>{r.get('bin','')}</td>
            <td>{r.get('total_screens',0)}</td>
            <td>{r.get('total_blocks',0)}</td>
            <td>{r.get('total_disputes',0)}</td>
            <td style="color:{color}">{ratio:.1%}</td>
        </tr>"""
    html += "</table>"
    return html


def _rules_table(rows: list[dict]) -> str:
    if not rows:
        return '<div class="empty">No rules configured</div>'
    html = "<table><tr><th>Name</th><th>Field</th><th>Operator</th><th>Value</th><th>Action</th><th>Priority</th></tr>"
    for r in rows:
        action = r.get("action", "")
        badge = f"badge-{action}"
        html += f"""<tr>
            <td>{r.get('name','')}</td>
            <td>{r.get('field','')}</td>
            <td>{r.get('operator','')}</td>
            <td>{r.get('value','')}</td>
            <td><span class="badge {badge}">{action.upper()}</span></td>
            <td>{r.get('priority',0)}</td>
        </tr>"""
    html += "</table>"
    return html


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(repo: Repository = Depends(get_repo)):
    summary = await repo.get_summary(hours=24)
    transactions = await repo.get_transactions(limit=20)
    blocked = await repo.get_transactions(decision="block", limit=20)
    top_bins = await repo.get_top_bins(limit=10)
    rules = await repo.get_rules()

    block_rate = f"{summary['block_rate']*100:.1f}" if summary["total_screened"] > 0 else "0"

    html = DASHBOARD_HTML
    html = html.replace("{{total_screened}}", str(summary["total_screened"]))
    html = html.replace("{{total_approved}}", str(summary["total_approved"]))
    html = html.replace("{{total_blocked}}", str(summary["total_blocked"]))
    html = html.replace("{{total_flagged}}", str(summary["total_flagged"]))
    html = html.replace("{{block_rate}}", block_rate)
    html = html.replace("{{dispute_count}}", str(summary["dispute_count"]))
    html = html.replace("{{transactions_table}}", _txn_table(transactions))
    html = html.replace("{{blocked_table}}", _txn_table(blocked))
    html = html.replace("{{bins_table}}", _bins_table(top_bins))
    html = html.replace("{{rules_table}}", _rules_table(rules))

    return HTMLResponse(content=html)
