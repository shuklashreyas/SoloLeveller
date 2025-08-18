from __future__ import annotations
from pathlib import Path
from datetime import date
import json
from typing import Dict, Any, List
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
        if cat != "boosts":
            return "Not a boost token"

        if name.startswith("physical booster"):
            self._set_trait_boost("Physical", 0.25)
            return "+25% XP to Physical Atones (today)"
        if name.startswith("omni booster"):
            self._set_global_boost(0.10)
            return "+10% XP to all Atones (today)"
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


# singleton instance
effects = ShopEffects()
