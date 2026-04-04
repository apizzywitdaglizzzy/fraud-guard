from __future__ import annotations

from enum import Enum


class RiskDecision(str, Enum):
    APPROVE = "approve"
    BLOCK = "block"
    FLAG = "flag"


class CardType(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    PREPAID = "prepaid"
    UNKNOWN = "unknown"


class RuleAction(str, Enum):
    BLOCK = "block"
    FLAG = "flag"
    ALLOW = "allow"


class RuleField(str, Enum):
    COUNTRY = "country"
    BIN = "bin"
    CARD_TYPE = "card_type"
    VELOCITY_IP_1M = "velocity_ip_1m"
    VELOCITY_IP_1H = "velocity_ip_1h"
    VELOCITY_CARD_1H = "velocity_card_1h"
    VELOCITY_EMAIL_1H = "velocity_email_1h"
    AMOUNT = "amount"
    IS_PREPAID = "is_prepaid"
