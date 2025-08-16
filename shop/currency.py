"""Simple currency manager using get_meta/set_meta for persistence.
Stores daily/week counters to enforce caps.
"""
from datetime import date, datetime, timedelta
from typing import Tuple

from database import get_meta, set_meta

COIN_DAILY_CAP = 150
SHARD_WEEKLY_CAP = 5

def _iso_day(d: date) -> str:
    return d.isoformat()

def _week_start(d: date) -> str:
    # ISO week start as YYYY-Www
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"

def init():
    # Ensure keys exist
    if get_meta("coins_total") is None:
        set_meta("coins_total", "0")
    if get_meta("coins_today") is None:
        set_meta("coins_today", "0")
    if get_meta("coins_last_day") is None:
        set_meta("coins_last_day", _iso_day(date.today()))
    if get_meta("shards_total") is None:
        set_meta("shards_total", "0")
    if get_meta("shards_week") is None:
        set_meta("shards_week", "0")
    if get_meta("shards_week_start") is None:
        set_meta("shards_week_start", _week_start(date.today()))

def reset_daily_if_needed():
    today = date.today()
    last = get_meta("coins_last_day") or ""
    if last != _iso_day(today):
        set_meta("coins_today", "0")
        set_meta("coins_last_day", _iso_day(today))

    # weekly shards reset
    cur_week = _week_start(today)
    week_start = get_meta("shards_week_start") or ""
    if week_start != cur_week:
        set_meta("shards_week", "0")
        set_meta("shards_week_start", cur_week)

# -- getters --
def get_coins() -> int:
    reset_daily_if_needed()
    return int(get_meta("coins_total") or 0)

def get_coins_today() -> int:
    reset_daily_if_needed()
    return int(get_meta("coins_today") or 0)

def get_shards() -> int:
    reset_daily_if_needed()
    return int(get_meta("shards_total") or 0)

def get_shards_week() -> int:
    reset_daily_if_needed()
    return int(get_meta("shards_week") or 0)

# -- modifiers --
def add_coins(amount: int) -> int:
    """Add coins, respecting daily cap. Returns actual delta applied (may be 0).
    amount may be negative to spend.
    """
    reset_daily_if_needed()
    total = int(get_meta("coins_total") or 0)
    today = int(get_meta("coins_today") or 0)

    if amount >= 0:
        allowed = max(0, COIN_DAILY_CAP - today)
        apply_amt = min(allowed, amount)
        total += apply_amt
        today += apply_amt
    else:
        # spending: allow if enough total
        spend = -amount
        if spend > total:
            return 0
        total -= spend
        # reduce today's count proportionally if possible
        today = max(0, today - spend)
        apply_amt = -spend

    set_meta("coins_total", str(total))
    set_meta("coins_today", str(today))
    return apply_amt

def add_shards(amount: int) -> int:
    reset_daily_if_needed()
    total = int(get_meta("shards_total") or 0)
    week = int(get_meta("shards_week") or 0)

    if amount >= 0:
        allowed = max(0, SHARD_WEEKLY_CAP - week)
        apply_amt = min(allowed, amount)
        total += apply_amt
        week += apply_amt
    else:
        spend = -amount
        if spend > total:
            return 0
        total -= spend
        week = max(0, week - spend)
        apply_amt = -spend

    set_meta("shards_total", str(total))
    set_meta("shards_week", str(week))
    return apply_amt

# helper to set absolute values (for debugging/tests)
def set_coins_total(n: int):
    set_meta("coins_total", str(n))

def set_shards_total(n: int):
    set_meta("shards_total", str(n))
