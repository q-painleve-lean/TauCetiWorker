"""Codex credits: whether the account's credits extend a spent ChatGPT usage window.

Once a ChatGPT plan's included usage is spent, Codex keeps running on the account's credits. The usage
endpoint then reports the plan's own limit as reached (`rate_limit.limit_reached`, `allowed`), which says
nothing about whether the credits still cover a request; `credits` says that. The pacer reads only the
plan's windows, so without this a spent window is `exhausted` and every Codex worker waits for the reset
with credits left.

With TAUCETI_CODEX_CREDIT_FLOOR set, `Quota._codex_from_payload` reads a spent window as over pace while
the balance stays above the floor: real quota remains, so an `ignore_quota` worker runs and a paced worker
still waits. Unset, empty, negative or not a finite number, credits are never spent (upstream behaviour).
"""

from __future__ import annotations

import math
import os

FLOOR_ENV = "TAUCETI_CODEX_CREDIT_FLOOR"


def floor() -> float | None:
    """The balance at which credit spending stops, or None when credits are not to be spent."""
    raw = os.environ.get(FLOOR_ENV, "").strip()
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if math.isfinite(value) and value >= 0 else None


def spendable(payload: dict) -> bool:
    """Whether the account may keep running Codex on credits above the floor: `has_credits` with a
    balance above it, or `unlimited`, and the overage limit not reached. Anything missing or malformed
    reads as no, so a schema change fails closed to upstream's exhausted window."""
    limit = floor()
    credits = payload.get("credits")
    if limit is None or not isinstance(credits, dict):
        return False
    if credits.get("overage_limit_reached") is not False:
        return False
    if credits.get("unlimited") is True:
        return True
    if credits.get("has_credits") is not True:
        return False
    balance = credits.get("balance")
    if isinstance(balance, bool):
        return False
    try:
        value = float(balance)
    except (TypeError, ValueError):
        return False
    return math.isfinite(value) and value > limit
