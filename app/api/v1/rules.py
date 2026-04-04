from __future__ import annotations

import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.db.repository import Repository
from app.dependencies import get_repo, get_rule_engine
from app.models.domain import RuleCreate, RuleResponse, RuleUpdate
from app.services.rule_engine import RuleEngine

router = APIRouter(prefix="/rules")


@router.get("", response_model=list[RuleResponse])
async def list_rules(repo: Repository = Depends(get_repo)):
    rows = await repo.get_rules()
    return [_row_to_response(r) for r in rows]


@router.post("", response_model=RuleResponse, status_code=201)
async def create_rule(
    rule: RuleCreate,
    repo: Repository = Depends(get_repo),
    rule_engine: RuleEngine = Depends(get_rule_engine),
):
    rule_id = f"rule_{uuid.uuid4().hex[:12]}"
    await repo.create_rule(
        id=rule_id, name=rule.name, field=rule.field.value,
        operator=rule.operator, value=json.dumps(rule.value),
        action=rule.action.value, priority=rule.priority, enabled=rule.enabled,
    )
    if rule_engine:
        rule_engine.invalidate_cache()
    row = await repo.get_rule(rule_id)
    return _row_to_response(row)


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str, rule: RuleUpdate,
    repo: Repository = Depends(get_repo),
    rule_engine: RuleEngine = Depends(get_rule_engine),
):
    existing = await repo.get_rule(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")

    updates = {}
    if rule.name is not None:
        updates["name"] = rule.name
    if rule.field is not None:
        updates["field"] = rule.field.value
    if rule.operator is not None:
        updates["operator"] = rule.operator
    if rule.value is not None:
        updates["value"] = json.dumps(rule.value)
    if rule.action is not None:
        updates["action"] = rule.action.value
    if rule.priority is not None:
        updates["priority"] = rule.priority
    if rule.enabled is not None:
        updates["enabled"] = int(rule.enabled)

    await repo.update_rule(rule_id, updates)
    if rule_engine:
        rule_engine.invalidate_cache()
    row = await repo.get_rule(rule_id)
    return _row_to_response(row)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: str,
    repo: Repository = Depends(get_repo),
    rule_engine: RuleEngine = Depends(get_rule_engine),
):
    existing = await repo.get_rule(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Rule not found")
    await repo.delete_rule(rule_id)
    if rule_engine:
        rule_engine.invalidate_cache()


def _row_to_response(row: dict) -> RuleResponse:
    return RuleResponse(
        id=row["id"], name=row["name"], field=row["field"],
        operator=row["operator"], value=json.loads(row["value"]),
        action=row["action"], priority=row["priority"],
        enabled=bool(row["enabled"]),
        created_at=row["created_at"], updated_at=row["updated_at"],
    )
