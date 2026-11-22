#!/usr/bin/env python3
"""A spent Codex window that the account's credits extend reads as over pace while the balance stays
above TAUCETI_CODEX_CREDIT_FLOOR, so --ignore-quota runs and a paced worker still waits. Without the
floor, or at or below it, the window stays exhausted (a hard block).
"""

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
os.environ.pop("TAUCETI_CONF", None)
import tauceti_worker as tc  # noqa: E402
from tauceti_worker.loop import _ignore_quota_verdict  # noqa: E402

WEEK = 7 * 24 * 3600
q = tc.Quota.__new__(tc.Quota)
fails = 0


def case(name, got, want):
    global fails
    ok = got == want
    fails += not ok
    print(f"{'ok  ' if ok else 'FAIL'} {name}" + ("" if ok else f": got {got!r}, want {want!r}"))


def payload(used=100, *, allowed=True, limit_reached=False, has_credits=True, unlimited=False,
            overage=False, balance="59004.9747765000"):
    # The shape the endpoint returned for a pro account whose weekly window was spent.
    return {
        "plan_type": "pro",
        "rate_limit": {
            "allowed": allowed,
            "limit_reached": limit_reached,
            "primary_window": {"used_percent": used, "limit_window_seconds": WEEK, "reset_after_seconds": 167438},
            "secondary_window": None,
        },
        "credits": {"has_credits": has_credits, "unlimited": unlimited, "overage_limit_reached": overage,
                    "balance": balance},
    }


def status(p):
    prov = q._codex_from_payload(p)
    return [w.status for w in prov.windows], prov.available, _ignore_quota_verdict(None, prov)


def with_floor(value):
    if value is None:
        os.environ.pop("TAUCETI_CODEX_CREDIT_FLOOR", None)
    else:
        os.environ["TAUCETI_CODEX_CREDIT_FLOOR"] = value


try:
    with_floor("20000")
    case("credits above the floor: over pace, not available", status(payload()), (["over-pace"], False, "over-pace"))
    case("the plan's own limit reached does not stop credit spending",
         status(payload(allowed=False, limit_reached=True)), (["over-pace"], False, "over-pace"))
    case("unlimited credits", status(payload(unlimited=True, has_credits=False, balance=None))[2], "over-pace")
    case("a window with headroom is untouched", status(payload(used=10))[0], ["under-pace"])

    missing = payload()
    del missing["credits"]["overage_limit_reached"]
    for name, p in (
        ("balance at the floor", payload(balance="20000")),
        ("balance below the floor", payload(balance="19999.5")),
        ("no credits", payload(has_credits=False)),
        ("overage limit reached", payload(overage=True)),
        ("limit reached and below the floor", payload(allowed=False, limit_reached=True, balance="19999.5")),
        ("unreadable balance", payload(balance="not a number")),
        ("boolean balance", payload(balance=True)),
        ("no credits block", {k: v for k, v in payload().items() if k != "credits"}),
        ("no overage flag", missing),
    ):
        case(f"stays exhausted: {name}", status(p), (["exhausted"], False, "wait"))

    for value in (None, "", "-1", "inf", "nan", "lots"):
        with_floor(value)
        case(f"no floor ({value!r}): upstream's exhausted window", status(payload()), (["exhausted"], False, "wait"))
finally:
    with_floor(None)

print(f"\n{'PASS' if not fails else 'FAIL'}: {fails} mismatch(es)")
sys.exit(1 if fails else 0)
