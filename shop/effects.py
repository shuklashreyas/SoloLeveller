from __future__ import annotations
from pathlib import Path
from datetime import date, datetime
import json
from math import prod

try:
    from constants import SIN_TO_ATTRIBUTE
except Exception:
    SIN_TO_ATTRIBUTE = {}

STATE_PATH = Path("data/shop_state.json")

def _today_iso() -> str:
    return date.today().isoformat()

def _clamp_daily_cap(mult: float, cap: float = 1.75) -> float:
    return min(mult, cap)

class ShopEffects:
    def __init__(self):
        self.state = {
            "day": _today_iso(),
            "active": {
                "xp_global": 0.0,
                "xp_trait": {},
                "contract_focus": 0.0,
                "streak_plus": 0.0,
                "dd_xp_bonus": 0.0,
                "logger_full_bonus": 0.0,
                "challenge_xp": 0.0,
                "sin_trait_reduce": {},
                "wrath_halved": False,
                "gentle_landing_charges": 0,
                "pardon_once": 0,
                "slip_insurance": 0,
                "dd_rerolls": 0,
                "challenge_rerolls": 0,
                "challenge_time_cushion": 0,
                "challenge_safe_decline": 0,
                "offer_beacons": 0,
                "contract_shields": 0,
                "grace_periods": 0,
                "logger_task_doubler": 0,
                "logger_penalty_buffer": 0.0,
            },
        }
        self._load()

    def _load(self):
        try:
            if STATE_PATH.exists():
                self.state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        self.reset_if_new_day()

    def _save(self):
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        except Exception:
            pass

    def reset_if_new_day(self):
        if self.state.get("day") != _today_iso():
            a = self.state.get("active", {})
            a.update({
                "xp_global": 0.0,
                "xp_trait": {},
                "contract_focus": 0.0,
                "streak_plus": 0.0,
                "dd_xp_bonus": 0.0,
                "logger_full_bonus": 0.0,
                "challenge_xp": 0.0,
                "sin_trait_reduce": {},
                "wrath_halved": False,
                "gentle_landing_charges": 0,
                "pardon_once": 0,
            })
            self.state["day"] = _today_iso()
            self._save()

    def activate_from_token(self, token: dict) -> str:
        name = (token.get("item") or "").strip().lower()
        cat  = (token.get("category") or "").strip().lower()
        if name.startswith("physical booster"):
            self._set_trait_boost("Physical", 0.25)
            return self._ok("+25% XP to Physical Atones (today)")
        if name.startswith("mindful booster"):
            self._set_trait_boost("Mindful", 0.25);  return self._ok("+25% XP to Mindful (today)")
        if name.startswith("spiritual booster"):
            self._set_trait_boost("Spiritual", 0.25); return self._ok("+25% XP to Spiritual (today)")
        if name.startswith("intellect booster"):
            self._set_trait_boost("Intellect", 0.25); return self._ok("+25% XP to Intellect (today)")
        if name.startswith("social booster"):
            self._set_trait_boost("Social", 0.25);    return self._ok("+25% XP to Social (today)")
        if name.startswith("integrity booster"):
            self._set_trait_boost("Integrity", 0.25); return self._ok("+25% XP to Integrity (today)")
        if name.startswith("omni booster"):
            self.state["active"]["xp_global"] = max(self.state["active"]["xp_global"], 0.10)
            return self._ok("+10% XP to all Atones (today)")
        if name.startswith("contract focus"):
            self.state["active"]["contract_focus"] = max(self.state["active"]["contract_focus"], 0.25)
            return self._ok("+25% XP on Atones for active-contract trait (today)")
        if name.startswith("streak spark"):
            self.state["active"]["streak_plus"] = max(self.state["active"]["streak_plus"], 0.10)
            return self._ok("+0.10 to today's streak multiplier")
        if name.startswith("daily double amplifier"):
            self.state["active"]["dd_xp_bonus"] = max(self.state["active"]["dd_xp_bonus"], 0.50)
            return self._ok("+0.5× XP on Daily Double Atones (today)")
        if name.startswith("logger bonus"):
            self.state["active"]["logger_full_bonus"] = max(self.state["active"]["logger_full_bonus"], 0.25)
            return self._ok("+25% XP bonus when Logger is 100% (today)")
        if name.startswith("challenge booster"):
            self.state["active"]["challenge_xp"] = max(self.state["active"]["challenge_xp"], 0.50)
            return self._ok("+50% XP on Random Challenge success (today)")
        if name.startswith("mindful cushion"):
            self._set_sin_trait_reduce("Mindful", 0.25)
            return self._ok("Mindful-mapped Sins −25% penalty (today)")
        if name.startswith("gentle landing"):
            self.state["active"]["gentle_landing_charges"] += 3
            return self._ok("Next 3 Sins −1 (today)")
        if name.startswith("one-time pardon"):
            self.state["active"]["pardon_once"] += 1
            return self._ok("Erase one Sin entry ≤ −2 (once)")
        if name.startswith("wrath ward"):
            self.state["active"]["wrath_halved"] = True
            return self._ok("Wrath penalties halved (today)")
        if name.startswith("slip insurance"):
            self.state["active"]["slip_insurance"] += 1
            return self._ok("If you miss a day, streak halves instead of reset (once)")
        if name.startswith("offer beacon"):
            self.state["active"]["offer_beacons"] += 1
            return self._ok("Offer Beacon ready (use when you open Contracts)")
        if name.startswith("contract shield"):
            self.state["active"]["contract_shields"] += 1
            return self._ok("Next broken contract −50% penalty (once)")
        if name.startswith("grace period"):
            self.state["active"]["grace_periods"] += 1
            return self._ok("Add +1 day to one active contract (once)")
        if name.startswith("task doubler"):
            self.state["active"]["logger_task_doubler"] += 1
            return self._ok("Mark one Logger task as double (tomorrow)")
        if name.startswith("planner’s edge") or name.startswith("planners edge"):
            self.state["active"]["logger_full_bonus"] = max(self.state["active"]["logger_full_bonus"], 0.50)
            return self._ok("Logger full-complete bonus +50% (tomorrow)")
        if name.startswith("penalty buffer"):
            self.state["active"]["logger_penalty_buffer"] = max(self.state["active"]["logger_penalty_buffer"], 0.30)
            return self._ok("Logger shortfall penalty −30% (tomorrow)")
        if name.startswith("challenge reroll"):
            self.state["active"]["challenge_rerolls"] += 1
            return self._ok("Challenge Reroll +1 (consumable)")
        if name.startswith("time cushion"):
            self.state["active"]["challenge_time_cushion"] += 300
            return self._ok("+5 min to a challenge timer (consumable)")
        if name.startswith("safe decline"):
            self.state["active"]["challenge_safe_decline"] += 1
            return self._ok("Safe Decline +1 (consumable)")
        if name.startswith("daily double reroll"):
            self.state["active"]["dd_rerolls"] += 1
            return self._ok("Daily Double Reroll +1 (consumable)")
        self._save()
        return f"Activated: {token.get('item')}"

    def _ok(self, msg: str) -> str:
        self._save()
        return msg

    def _set_trait_boost(self, trait: str, pct: float):
        t = self.state["active"].setdefault("xp_trait", {})
        t[trait] = max(t.get(trait, 0.0), pct)
        self._save()

    def _set_sin_trait_reduce(self, trait: str, pct: float):
        t = self.state["active"].setdefault("sin_trait_reduce", {})
        t[trait] = max(t.get(trait, 0.0), pct)
        self._save()

    def xp_after_boosts(self, base_xp: int | float, *, trait: str,
                        has_contract_for_trait: bool = False,
                        is_random_challenge: bool = False,
                        is_daily_double: bool = False) -> int:
        a = self.state["active"]
        mults = []
        if a.get("xp_global", 0) > 0:
            mults.append(1 + a["xp_global"])
        t = a.get("xp_trait", {}).get(trait, 0.0)
        if t > 0:
            mults.append(1 + t)
        if has_contract_for_trait and a.get("contract_focus", 0) > 0:
            mults.append(1 + a["contract_focus"])
        if is_random_challenge and a.get("challenge_xp", 0) > 0:
            mults.append(1 + a["challenge_xp"])
        final = base_xp * _clamp_daily_cap(prod(mults) if mults else 1.0)
        if is_daily_double and a.get("dd_xp_bonus", 0) > 0:
            final *= (1 + a["dd_xp_bonus"])
        return int(round(final))

    def extra_streak_delta(self) -> float:
        return float(self.state["active"].get("streak_plus", 0.0) or 0.0)

    def reduce_sin_penalty(self, *, sin_name: str, mapped_trait: str,
                           penalty_points: int | float) -> int:
        a = self.state["active"]
        reduce_pct = a.get("sin_trait_reduce", {}).get(mapped_trait, 0.0)
        p = float(penalty_points)
        if sin_name.strip().lower() == "wrath" and a.get("wrath_halved"):
            reduce_pct = max(reduce_pct, 0.50)
        reduce_pct = min(reduce_pct, 0.50)
        p *= (1.0 - reduce_pct)
        if a.get("gentle_landing_charges", 0) > 0 and p > 0:
            a["gentle_landing_charges"] -= 1
            p = max(0.0, p - 1.0)
            self._save()
        return int(round(p))

    def consume_dd_reroll(self) -> bool:
        a = self.state["active"]
        if a.get("dd_rerolls", 0) > 0:
            a["dd_rerolls"] -= 1; self._save(); return True
        return False

    def dd_rerolls_left(self) -> int:
        return int(self.state["active"].get("dd_rerolls", 0) or 0)

    def consume_challenge_reroll(self) -> bool:
        a = self.state["active"]
        if a.get("challenge_rerolls", 0) > 0:
            a["challenge_rerolls"] -= 1; self._save(); return True
        return False

    def pop_challenge_time_cushion(self) -> int:
        a = self.state["active"]
        sec = int(a.get("challenge_time_cushion", 0) or 0)
        a["challenge_time_cushion"] = 0
        if sec: self._save()
        return sec

    def consume_challenge_safe_decline(self) -> bool:
        a = self.state["active"]
        if a.get("challenge_safe_decline", 0) > 0:
            a["challenge_safe_decline"] -= 1; self._save(); return True
        return False

    def contract_shield_available(self) -> bool:
        return self.state["active"].get("contract_shields", 0) > 0

    def consume_contract_shield(self) -> bool:
        a = self.state["active"]
        if a.get("contract_shields", 0) > 0:
            a["contract_shields"] -= 1; self._save(); return True
        return False

    def logger_full_bonus_pct(self) -> float:
        return float(self.state["active"].get("logger_full_bonus", 0.0) or 0.0)

    def logger_penalty_buffer_pct(self) -> float:
        return float(self.state["active"].get("logger_penalty_buffer", 0.0) or 0.0)

    def dump(self) -> dict:
        return self.state

effects = ShopEffects()
