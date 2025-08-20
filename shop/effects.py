from __future__ import annotations
from pathlib import Path
from datetime import date
import json
from typing import Dict, Any, List
from constants import POSITIVE_TRAITS
from math import prod

STATE_PATH = Path("data/shop_state.json")


def _today_iso() -> str:
    return date.today().isoformat()


class ShopEffects:
    """Minimal boosts-only effects manager.

    Exposes:
    - activate_from_token(token_dict) -> str
    - xp_after_boosts(base_xp, trait=..., ...) -> int
    - dump() -> dict
    - extra_streak_delta() -> float
    """

    def __init__(self, state_path: Path = STATE_PATH) -> None:
        self.state_path = state_path
        self._state = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.state_path.exists():
            try:
                raw = self.state_path.read_text(encoding="utf-8")
                data = json.loads(raw or "{}")
                if isinstance(data, dict) and "day" in data and "active_date" not in data:
                    data["active_date"] = data.pop("day")
                return data
            except Exception:
                pass
        return {
            "active_date": _today_iso(),
            "active": {
                "xp_global": 0.0,
                "xp_trait": {},
                "contract_focus": 0.0,
                "streak_plus": 0.0,
                "dd_xp_bonus": 0.0,
                "challenge_xp": 0.0,
                # extra features
                "logger_full_bonus": 0.0,
                "logger_full_bonus_next": 0.0,
                "task_doubler": 0,
                "logger_penalty_buffer": 0.0,
                "logger_penalty_buffer_one_time": False,
                "wrath_halved": False,
                "gentle_landing_charges": 0,
                "offer_beacons": 0,
                "grace_periods": 0,
                "dd_rerolls": 0,
                "challenge_rerolls": 0,
                "challenge_time_cushion": 0,
                "contract_shields": 0,
            },
        }

    def _save(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps(self._state, indent=2), encoding="utf-8")
        except Exception:
            pass

    def dump(self) -> Dict[str, Any]:
        return {"active_date": self._state.get("active_date"), "active": dict(self._state.get("active", {}))}

    def extra_streak_delta(self) -> float:
        return float(self._state.get("active", {}).get("streak_plus", 0.0) or 0.0)

    def _set_trait_boost(self, trait: str, pct: float) -> None:
        a = self._state.setdefault("active", {})
        tmap = a.setdefault("xp_trait", {})
        tmap[trait] = max(float(tmap.get(trait, 0.0) or 0.0), float(pct))
        a["xp_trait"] = tmap
        self._save()

    def _set_global_boost(self, pct: float) -> None:
        a = self._state.setdefault("active", {})
        a["xp_global"] = max(float(a.get("xp_global", 0.0) or 0.0), float(pct))
        self._save()

    def activate_from_token(self, token: dict) -> str:
        name = (token.get("item") or "").strip().lower() if isinstance(token, dict) else str(token)
        cat = (token.get("category") or "").strip().lower() if isinstance(token, dict) else ""

        # Omni/global
        if name.startswith("omni booster"):
            self._set_global_boost(0.10)
            return "+10% XP to all Atones (today)"

        # Trait-specific boosters (e.g. 'Spiritual Booster', 'Mindful Booster')
        for trait in POSITIVE_TRAITS:
            if name.startswith(f"{trait.lower()} booster"):
                self._set_trait_boost(trait, 0.25)
                return f"+25% XP to {trait} Atones (today)"

        # legacy Physical Booster name
        if name.startswith("physical booster"):
            self._set_trait_boost("Physical", 0.25)
            return "+25% XP to Physical Atones (today)"
        # Contract focus booster
        if name.startswith("contract focus booster"):
            a = self._state.setdefault("active", {})
            a["contract_focus"] = max(float(a.get("contract_focus", 0.0) or 0.0), 0.25)
            self._save()
            return "+25% XP when matching a contract (today)"
        # Logger full booster
        if name.startswith("logger full booster"):
            a = self._state.setdefault("active", {})
            a["logger_full_bonus"] = max(float(a.get("logger_full_bonus", 0.0) or 0.0), 0.20)
            self._save()
            return "+20% XP when logging a full journal (today)"
        # Gentle landing (sin penalty reduction) — grant 3 charges
        if name.startswith("gentle landing"):
            a = self._state.setdefault("active", {})
            a["gentle_landing_charges"] = max(int(a.get("gentle_landing_charges", 0) or 0), 3)
            self._save()
            return "Gentle Landing active: next 3 sin penalties reduced by 1 XP each (today)"
        # Wrath halver
        if name.startswith("wrath halver"):
            a = self._state.setdefault("active", {})
            a["wrath_halved"] = True
            self._save()
            return "Wrath penalties halved (today)"
        # Mindful Cushion (trait-specific sin reduction)
        if name.startswith("mindful cushion"):
            # maps to Mindful trait reductions
            self._set_sin_trait_reduce("Mindful", 0.25)
            return "Mindful Cushion active: -25% Mindful sin penalties (today)"
        # One-Time Pardon
        if name.startswith("one-time pardon") or name.startswith("one time pardon"):
            a = self._state.setdefault("active", {})
            a["one_time_pardons"] = int(a.get("one_time_pardons", 0) or 0) + 1
            self._save()
            return "One-Time Pardon granted: erase one small Sin (today)"
        # Slip Insurance
        if name.startswith("slip insurance"):
            a = self._state.setdefault("active", {})
            a["slip_insurance"] = int(a.get("slip_insurance", 0) or 0) + 1
            self._save()
            return "Slip Insurance active: halve your streak on a miss instead of resetting (one-time)"
        # Offer beacon
        if name.startswith("offer beacon"):
            a = self._state.setdefault("active", {})
            a["offer_beacons"] = int(a.get("offer_beacons", 0) or 0) + 1
            self._save()
            return "+1 Offer Beacon (adds an offer)"
        # Grace Period (extend one active contract by +1 day)
        if name.startswith("grace period"):
            a = self._state.setdefault("active", {})
            a["grace_periods"] = int(a.get("grace_periods", 0) or 0) + 1
            self._save()
            return "+1 Grace Period (extend one contract by 1 day)"
        # Daily Double reroll
        if name.startswith("daily double reroll"):
            a = self._state.setdefault("active", {})
            a["dd_rerolls"] = int(a.get("dd_rerolls", 0) or 0) + 1
            self._save()
            return "One extra Daily Double reroll available (today)"
        # Challenge reroll
        if name.startswith("challenge reroll"):
            a = self._state.setdefault("active", {})
            a["challenge_rerolls"] = int(a.get("challenge_rerolls", 0) or 0) + 1
            self._save()
            return "One extra Challenge reroll available (today)"
        # Challenge time cushion
        if name.startswith("challenge time cushion"):
            a = self._state.setdefault("active", {})
            a["challenge_time_cushion"] = max(int(a.get("challenge_time_cushion", 0) or 0), 300)
            self._save()
            return "+5 min added to challenge timers (today)"
        # Contract shield
        if name.startswith("contract shield"):
            a = self._state.setdefault("active", {})
            a["contract_shields"] = int(a.get("contract_shields", 0) or 0) + 1
            self._save()
            return "Contract shield granted (protects one contract today)"
        # Small global XP multiplier
        if name.startswith("xp multiplier small"):
            self._set_global_boost(0.05)
            return "+5% XP to all Atones (today)"
        if name.startswith("streak spark"):
            a = self._state.setdefault("active", {})
            a["streak_plus"] = max(float(a.get("streak_plus", 0.0) or 0.0), 0.10)
            self._save()
            return "+0.10 to today's streak multiplier"
        if name.startswith("daily double amplifier"):
            a = self._state.setdefault("active", {})
            a["dd_xp_bonus"] = max(float(a.get("dd_xp_bonus", 0.0) or 0.0), 0.50)
            self._save()
            return "+0.5× XP on Daily Double Atones (today)"
        if name.startswith("challenge booster"):
            a = self._state.setdefault("active", {})
            a["challenge_xp"] = max(float(a.get("challenge_xp", 0.0) or 0.0), 0.50)
            self._save()
            return "+50% XP on Random Challenge success (today)"

        # --- Logger category tokens ---
        # Task Doubler: one logged task counts as two for the logger bonus calc (one-time)
        if name.startswith("task doubler"):
            a = self._state.setdefault("active", {})
            a["task_doubler"] = int(a.get("task_doubler", 0) or 0) + 1
            self._save()
            return "Task Doubler granted: one logged task will count as two (one-time)"

        # Planner's Edge: schedule a logger full bonus for tomorrow
        if name.startswith("planner") or name.startswith("planner's edge"):
            a = self._state.setdefault("active", {})
            # store as a 'next' flag which will be applied when the logger opens next day
            a["logger_full_bonus_next"] = max(float(a.get("logger_full_bonus_next", 0.0) or 0.0), 0.50)
            self._save()
            return "Planner's Edge scheduled: +50% logger full bonus for tomorrow"

        # Penalty Buffer: one-time reduction to logger penalty
        if name.startswith("penalty buffer"):
            a = self._state.setdefault("active", {})
            a["logger_penalty_buffer"] = max(float(a.get("logger_penalty_buffer", 0.0) or 0.0), 0.30)
            # mark as one-time use — we will zero it when applied
            a["logger_penalty_buffer_one_time"] = True
            self._save()
            return "Penalty Buffer active: -30% logger penalty on next incomplete set"

        return "Unknown boost"

    def xp_after_boosts(self, base_xp: float, *, trait: str, has_contract_for_trait: bool = False, is_random_challenge: bool = False, is_daily_double: bool = False) -> int:
        a = self._state.get("active", {})
        mults: List[float] = []
        g = float(a.get("xp_global", 0.0) or 0.0)
        if g > 0:
            mults.append(1.0 + g)
        t = float((a.get("xp_trait", {}) or {}).get(trait, 0.0) or 0.0)
        if t > 0:
            mults.append(1.0 + t)
        if has_contract_for_trait and float(a.get("contract_focus", 0.0) or 0.0) > 0:
            mults.append(1.0 + float(a.get("contract_focus", 0.0)))
        if is_random_challenge and float(a.get("challenge_xp", 0.0) or 0.0) > 0:
            mults.append(1.0 + float(a.get("challenge_xp", 0.0)))

        prod_mult = prod(mults) if mults else 1.0
        cap = 1.75
        final = base_xp * min(prod_mult, cap)

        dd_bonus = float(a.get("dd_xp_bonus", 0.0) or 0.0)
        if is_daily_double and dd_bonus > 0:
            final *= (1.0 + dd_bonus)

        try:
            print(f"[effects.debug] base={base_xp} prod_mult={prod_mult:.4f} clamped_mult={min(prod_mult, cap):.4f} final={int(round(final))}")
        except Exception:
            pass

        return int(round(final))

    # --- Neglects / Sin penalty helpers ---
    def logger_penalty_buffer_pct(self) -> float:
        a = self._state.get("active", {})
        return float(a.get("logger_penalty_buffer", 0.0) or 0.0)

    def logger_full_bonus_pct(self) -> float:
        a = self._state.get("active", {})
        return float(a.get("logger_full_bonus", 0.0) or 0.0)

    def consume_logger_penalty_buffer(self) -> None:
        """Consume the one-time logger penalty buffer (set it to 0)."""
        a = self._state.setdefault("active", {})
        if float(a.get("logger_penalty_buffer", 0.0) or 0.0) > 0:
            a["logger_penalty_buffer"] = 0.0
            a["logger_penalty_buffer_one_time"] = False
            try:
                self._save()
            except Exception:
                pass

    def shift_logger_next_to_active(self) -> None:
        """If planner-edge was scheduled for next day, apply it to active bonuses and clear the next flag."""
        a = self._state.setdefault("active", {})
        next_pct = float(a.get("logger_full_bonus_next", 0.0) or 0.0)
        if next_pct > 0:
            a["logger_full_bonus"] = max(float(a.get("logger_full_bonus", 0.0) or 0.0), next_pct)
            a["logger_full_bonus_next"] = 0.0
            try:
                self._save()
            except Exception:
                pass

    def reduce_sin_penalty(self, *, sin_name: str, mapped_trait: str, penalty_points: int) -> int:
        """Apply active neglects to a sin penalty and return the (non-negative) reduced penalty points.

        Rules:
        - Reductions cap at 50% of the original penalty.
        - Gentle Landing consumes one charge and reduces penalty by 1 XP (per charge) but never flips negative->positive.
        - sin_trait_reduce entries (e.g., Mindful Cushion) reduce penalties for that trait by pct (up to 50%).
        - Wrath halving halves penalties for "Wrath" (also subject to 50% cap).
        - One-Time Pardon: if available and penalty_points <= 2, it erases the sin (returns 0) and consumes the pardon.
        - Slip Insurance is not applied here; it is consumed elsewhere when a miss is detected (flag left in state).
        """
        if penalty_points <= 0:
            return 0

        a = self._state.setdefault("active", {})
        original = int(penalty_points)

        # One-Time Pardon (shard consumable) - only erase small sins (<=2)
        if int(a.get("one_time_pardons", 0) or 0) > 0 and original <= 2:
            a["one_time_pardons"] = int(a.get("one_time_pardons", 0)) - 1
            self._save()
            return 0

        # Gentle Landing: consume one charge to reduce penalty by 1 (per charge)
        if int(a.get("gentle_landing_charges", 0) or 0) > 0:
            # consume one charge and reduce by 1 point
            a["gentle_landing_charges"] = int(a.get("gentle_landing_charges", 0)) - 1
            self._save()
            reduced = max(0, original - 1)
            # still apply other percentage reductions below to the reduced number
            original = reduced

        # Percent reductions (trait-specific cushions)
        sin_map = a.get("sin_trait_reduce", {}) or {}
        pct = float(sin_map.get(mapped_trait, 0.0) or 0.0)

        # Wrath halving
        if mapped_trait.lower() == "wrath" and bool(a.get("wrath_halved", False)):
            pct = max(pct, 0.5)

        # Ensure cap at 50%
        pct = min(pct, 0.5)

        reduced = int(round(original * (1.0 - pct)))

        # Never flip to positive — penalties are non-negative ints
        if reduced < 0:
            reduced = 0

        try:
            self._save()
        except Exception:
            pass

        return int(reduced)

    # Utility: set a sin-trait reduction (used by token activation)
    def _set_sin_trait_reduce(self, trait: str, pct: float) -> None:
        a = self._state.setdefault("active", {})
        smap = a.setdefault("sin_trait_reduce", {})
        smap[trait] = max(float(smap.get(trait, 0.0) or 0.0), float(pct))
        a["sin_trait_reduce"] = smap
        self._save()

    def consume_slip_insurance(self) -> bool:
        """Consume one Slip Insurance if available; returns True if consumed."""
        a = self._state.setdefault("active", {})
        if int(a.get("slip_insurance", 0) or 0) > 0:
            a["slip_insurance"] = int(a.get("slip_insurance", 0)) - 1
            self._save()
            return True
        return False

    def consume_contract_shield(self) -> bool:
        a = self._state.setdefault("active", {})
        if int(a.get("contract_shields", 0) or 0) > 0:
            a["contract_shields"] = int(a.get("contract_shields", 0)) - 1
            self._save()
            return True
        return False


# singleton instance
effects = ShopEffects()
