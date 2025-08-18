# ui/app/leveling.py
# XP rules (diminishing returns, contracts boost/debuff, streaks, soft caps)
# + Daily EMA baselines (form 14d, core 60d)

from datetime import date, datetime, timedelta
import re

from database import (
    get_meta, set_meta, get_entries_by_date,
    upsert_attribute, get_attributes
)

# ---------- Tunables ----------
STREAK_STEP = 0.06           # +6% per day
STREAK_CAP  = 0.75           # max +75% (→ 1.75x)
DIMINISH_STEPS = [1.00, 0.70, 0.40, 0.25]  # 0th, 1st repeat, 2nd, 3rd+
LOW_FLOOR_BONUS = 0.15       # +15% if trait score < 60
HIGH_SOFT_1     = (80, 0.85) # 80+ → 0.85x
HIGH_SOFT_2     = (90, 0.70) # 90+ → 0.70x
CONTRACT_BOOST  = 0.25       # +25% if a matching contract is active
BROKEN_DEBUFF   = 0.20       # -20% while debuff active

EMA_FORM_DAYS   = 14         # fast "form" baseline
EMA_CORE_DAYS   = 60         # slow "core" baseline

# ---------- Helpers ----------
def _today_iso() -> str:
    return date.today().isoformat()

def _alpha(n_days: int) -> float:
    return 2.0 / (n_days + 1.0)

def _norm(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())

_TRAIT_KEYS = None
def _trait_name_keys():
    global _TRAIT_KEYS
    if _TRAIT_KEYS is None:
        _TRAIT_KEYS = {}
        for name in get_attributes().keys():
            _TRAIT_KEYS[name] = [_norm(name)]
    return _TRAIT_KEYS

# ---------- Diminishing returns (same atone repeated today) ----------
def _same_atone_count_today(category: str, item: str) -> int:
    rows = get_entries_by_date(_today_iso())
    cnt = 0
    for r in rows:
        if r["entry_type"] == "ATONE" and r["category"] == category and r["item"] == item:
            cnt += 1
    return cnt

def _diminish_mult(previous_occurrences: int) -> float:
    # previous_occurrences = how many times this exact atone already logged today
    if previous_occurrences < 0:
        previous_occurrences = 0
    return DIMINISH_STEPS[min(previous_occurrences, len(DIMINISH_STEPS) - 1)]

# ---------- Streaks ----------
def _streak_count_to_mult(count: int) -> float:
    # 1.00 → up to 1.75 with STREAK_CAP
    bonus = min(count * STREAK_STEP, STREAK_CAP)
    return 1.0 + bonus

def update_streak_on_action():
    """Call on the FIRST successful log of a day (any action)."""
    today = _today_iso()
    last = get_meta("streak_last_day")
    count = int(get_meta("streak_count") or 0)

    if last == today:
        # already updated today
        pass
    else:
        if last:
            # distance in days
            diff = (date.fromisoformat(today) - date.fromisoformat(last)).days
            if diff == 1:
                count += 1                      # kept streak
            elif diff > 1:
                count = max(0, count // 2)      # missed → halve, not reset
        else:
            count = 1

        set_meta("streak_last_day", today)
        set_meta("streak_count", str(count))
        set_meta("streak_mult", f"{_streak_count_to_mult(count):.4f}")

from shop.effects import effects

def _streak_mult() -> float:
    try:
        base = float(get_meta("streak_mult") or "1.0")
    except Exception:
        base = 1.0
    # Add extra streak delta from effects engine
    return base + effects.extra_streak_delta()

# ---------- Soft caps / floors by current score ----------
def _softcap_mult(score: int) -> float:
    if score < 60:
        return 1.0 + LOW_FLOOR_BONUS
    if score >= HIGH_SOFT_2[0]:
        return HIGH_SOFT_2[1]
    if score >= HIGH_SOFT_1[0]:
        return HIGH_SOFT_1[1]
    return 1.0

# ---------- Contracts boost/debuff ----------
def _active_contract_titles() -> list[str]:
    # Prefer a DB helper if present; otherwise inline SQL.
    try:
        from database import get_active_contracts
        rows = get_active_contracts(_today_iso())
        return [r.get("title", "") for r in rows]
    except Exception:
        try:
            from database import get_connection
            import sqlite3
            conn = get_connection(); conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT title FROM contracts
                WHERE active=1 AND broken=0 AND (
                    (expires_at IS NULL AND date(?) BETWEEN date(start_date) AND date(end_date))
                    OR (expires_at IS NOT NULL AND datetime('now','localtime') <= datetime(expires_at))
                )
            """, (_today_iso(),))
            out = [r["title"] for r in cur.fetchall()]
            conn.close()
            return out
        except Exception:
            return []

def _contract_mult_for_trait(trait: str) -> float:
    trait_keys = _trait_name_keys().get(trait, [_norm(trait)])
    titles = _active_contract_titles()
    active_match = False
    for t in titles:
        nt = _norm(t)
        if any(k in nt for k in trait_keys):
            active_match = True
            break

    m = 1.0
    if active_match:
        m *= (1.0 + CONTRACT_BOOST)

    # temporary global debuff after breaking a contract
    debuff_until = get_meta("xp_debuff_until")  # ISO datetime
    if debuff_until:
        try:
            if datetime.now() <= datetime.fromisoformat(debuff_until):
                m *= (1.0 - BROKEN_DEBUFF)
        except Exception:
            pass

    return m

# ---------- Public: compute XP ----------
def compute_xp_gain(trait: str, category: str, item: str, pts: int, is_daily_double: bool = False):
    """
    Returns the *final* XP to add (already includes all multipliers).
    Accepts positive or negative pts (SIN stays negative).
    """
    base_xp = int(pts) * 10

    # Diminishing returns: how many times already logged today BEFORE we add this one
    prev = _same_atone_count_today(category, item)
    m_dim = _diminish_mult(prev)

    # Streak multiplier (already persisted daily)
    m_streak = _streak_mult()

    # Soft caps / floors by current score
    score = get_attributes().get(trait, {}).get("score", 50)
    m_soft = _softcap_mult(score)

    # Contracts (+ boost / possible debuff)
    m_ctr  = _contract_mult_for_trait(trait)

    total_mult = m_dim * m_streak * m_soft * m_ctr

    # Keep sign of base_xp (SIN negative)
    final = int(round(base_xp * total_mult))

    # Debug output to trace XP calculation before effects
    try:
        print(f"[xp.debug] base_xp={base_xp} prev_occurrences={prev} m_dim={m_dim:.4f} m_streak={m_streak:.4f} m_soft={m_soft:.4f} m_ctr={m_ctr:.4f} total_mult={total_mult:.4f} final_before_effects={final}")
    except Exception:
        pass

    # If this is an ATONE (positive XP), allow shop effects (global/trait/contract/challenge/dd)
    try:
        from shop.effects import effects
    except Exception:
        effects = None

    boost_delta = 0
    if base_xp > 0 and effects is not None:
        # effects.xp_after_boosts expects base_xp and trait name; it handles dd multiplier
        try:
            # Debug before delegating to effects
            try:
                print(f"[xp.debug] delegating to effects.xp_after_boosts with final_before={final} trait={trait} has_contract={(m_ctr>1.0)} is_random_challenge={(item.lower().find('challenge') != -1)} is_daily_double={is_daily_double}")
            except Exception:
                pass

            final_with_effects = effects.xp_after_boosts(final, trait=trait, has_contract_for_trait=(m_ctr > 1.0),
                                            is_random_challenge=(item.lower().find('challenge') != -1),
                                            is_daily_double=is_daily_double)
            # calculate boost delta applied by effects
            try:
                boost_delta = int(round(final_with_effects - final))
            except Exception:
                boost_delta = 0
            final = final_with_effects
            try:
                print(f"[xp.debug] final_after_effects={final}")
            except Exception:
                pass
        except Exception:
            # fallback to computed final if effects call fails
            final = int(round(base_xp * total_mult))

    # Optional floor: allow 0, but don't flip sign
    if base_xp > 0:
        final = max(0, int(final))
    else:
        final = min(0, int(final))
    # For callers that expect only an int, returning a tuple could break them.
    # The main action path (`parts_actions._handle_action`) will unpack the tuple.
    return final, boost_delta

# ---------- Baselines (EMA) ----------
def update_daily_emas_if_needed():
    """
    Once per day, update two EMA baselines from current *scores*:
      - form_ema:<Trait> (14d)
      - core_ema:<Trait> (60d)
    Also writes attributes.baseline = round(core_ema) so existing UI picks it up.
    """
    today = _today_iso()
    last = get_meta("ema_updated_day")
    if last == today:
        return

    form_a = _alpha(EMA_FORM_DAYS)
    core_a = _alpha(EMA_CORE_DAYS)

    scores = {t: v.get("score", 50) for t, v in get_attributes().items()}
    for trait, score in scores.items():
        # read previous EMAs (default to score)
        try:
            f_prev = float(get_meta(f"form_ema:{trait}") or score)
            c_prev = float(get_meta(f"core_ema:{trait}") or score)
        except Exception:
            f_prev = float(score); c_prev = float(score)

        f_now = form_a * score + (1.0 - form_a) * f_prev
        c_now = core_a * score + (1.0 - core_a) * c_prev

        set_meta(f"form_ema:{trait}", f"{f_now:.4f}")
        set_meta(f"core_ema:{trait}", f"{c_now:.4f}")

        # keep existing UI compatible: write attributes.baseline as the core EMA
        upsert_attribute(trait, int(round(c_now)), int(score))

    set_meta("ema_updated_day", today)

def get_form_core_baselines() -> dict[str, dict]:
    """
    Returns: {trait: {'form': float, 'core': float}}
    (handy if you later want to show both on the UI)
    """
    out = {}
    for trait in get_attributes().keys():
        try:
            f = float(get_meta(f"form_ema:{trait}") or 0)
            c = float(get_meta(f"core_ema:{trait}") or 0)
        except Exception:
            f = 0.0; c = 0.0
        out[trait] = {"form": f, "core": c}
    return out
