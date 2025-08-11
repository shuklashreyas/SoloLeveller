# exp_system.py
from typing import Dict
from constants import RANKS, STAT_MIN
from database import get_meta, set_meta

# XP curve: +50 per level step, starting at 100
def xp_to_next(level: int) -> int:
    return 100 + (level - 1) * 50

def xp_threshold(level: int) -> int:
    if level <= 1:
        return 0
    total = 0
    for l in range(1, level):
        total += xp_to_next(l)
    return total

def level_from_xp(total_xp: int) -> int:
    lvl = 1
    while total_xp >= xp_threshold(lvl + 1):
        lvl += 1
    return lvl

def xp_in_level(total_xp: int, level: int) -> int:
    return total_xp - xp_threshold(level)

# XP stored in meta["xp"]
def get_total_xp() -> int:
    val = get_meta("xp")
    try:
        return int(val) if val is not None else 0
    except ValueError:
        return 0

def set_total_xp(xp: int):
    set_meta("xp", str(max(0, int(xp))))

def add_total_xp(delta: int) -> int:
    new = max(0, get_total_xp() + int(delta))
    set_total_xp(new)
    return new

def average_stat(stats: Dict[str, int]) -> int:
    if not stats:
        return 0
    vals = [stats.get(k, STAT_MIN) for k in stats.keys()]
    return int(round(sum(vals) / len(vals)))

def compute_rank(avg: int) -> str:
    for lo, hi, name in RANKS:
        if lo <= avg <= hi:
            return name
    return "Unranked"
