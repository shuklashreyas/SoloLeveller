# ui/app/parts_actions.py
import random
import tkinter as tk
from tkinter import messagebox

from constants import (
    POSITIVE_TRAITS, SINS, SIN_TO_ATTRIBUTE, STAT_MIN,
    ATONE_MENU, SIN_MENU
)
from database import (
    insert_entry, get_daily_double, set_daily_double,
    get_attributes, update_attribute_score, get_journal, upsert_journal, get_meta, set_meta
)
from exp_system import level_from_xp, get_total_xp, add_total_xp
from shop.currency import add_coins, add_shards
from widgets import RoundButton
from ..dialogs import ask_action
from sound import play_sfx
from .leveling import compute_xp_gain, update_streak_on_action

# --- Journal ---
def save_journal(self, text: str):
    from datetime import date
    if self.current_date != date.today():
        return
    upsert_journal(self.current_date.isoformat(), text.strip())
    self.journal.note_saved()
    try:
        from animations import flash_widget
        flash_widget(self.journal.status_label, times=2, on="#C7F9CC")
    except Exception:
        pass

    # --- Journal streak: qualify if >=100 chars and award every 5 qualifying days ---
    try:
        qual = len((text or "").strip()) >= 100
        if qual:
            # persistent counter in meta: 'journal_streak_count' increments on each qualifying day
            try:
                cur = int(get_meta('journal_streak_count') or "0")
            except Exception:
                cur = 0
            cur += 1
            try:
                set_meta('journal_streak_count', str(cur))
            except Exception:
                pass

            # award 20 coins every 5 qualifying days
            if cur % 5 == 0:
                try:
                    add_coins(20)
                    try: play_sfx('bought')
                    except Exception: pass
                    # show small popup to notify user
                    try:
                        messagebox.showinfo('Journal Reward', 'Milestone reached: 20 coins awarded!')
                    except Exception:
                        pass
                except Exception:
                    pass

            # refresh the journal streak label if available
            try:
                if hasattr(self, 'journal') and hasattr(self.journal, '_update_streak_label'):
                    try: self.journal._update_streak_label()
                    except Exception: pass
            except Exception:
                pass
    except Exception:
        pass

# --- Actions ---
def open_atone_dialog(self):
    _handle_action(self, kind="ATONE")

def open_sin_dialog(self):
    _handle_action(self, kind="SIN")

def _handle_action(self, kind: str):
    from datetime import date
    if self.current_date != date.today():
        messagebox.showinfo("Not allowed", "You can only log for today.")
        return

    cats = POSITIVE_TRAITS if kind == "ATONE" else SINS
    menu_map = ATONE_MENU if kind == "ATONE" else SIN_MENU

    result = ask_action(
        root=self.root,
        title=("Atone" if kind == "ATONE" else "Sin"),
        categories=cats,
        menu_map=menu_map
    )
    if result is None:
        return

    category, item_text, pts = result  # pts>0 for atone; pts<0 for sin

    # Daily Double pick (seed if missing)
    day = self.current_date.isoformat()
    dd = get_daily_double(day)
    if not dd:
        dd = {"atone": random.choice(POSITIVE_TRAITS), "sin": random.choice(SINS)}
        set_daily_double(day, dd["atone"], dd["sin"])

    # Apply Daily Double to points (keeps SIN negative)
    is_daily_double = False
    if (kind == "ATONE" and category == dd["atone"]) or (kind == "SIN" and category == dd["sin"]):
        is_daily_double = True
        pts *= 2

    # Which positive trait moves?
    changed_attr = category if kind == "ATONE" else SIN_TO_ATTRIBUTE.get(category)

    # Old value for SFX
    old_val = None
    if changed_attr:
        old_val = get_attributes().get(changed_attr, {}).get("score", STAT_MIN)

    # Save entry
    insert_entry(
        date=self.current_date.isoformat(),
        entry_type=kind,
        category=category,
        item=item_text,
        points=pts
    )

    # Update streak on first log of the day
    update_streak_on_action()

    # Stat change
    if kind == "ATONE":
        update_attribute_score(category, abs(pts))
    else:
        if changed_attr:
            update_attribute_score(changed_attr, pts)

    # SFX: stat up/down
    if changed_attr is not None and old_val is not None:
        new_val = get_attributes().get(changed_attr, {}).get("score", STAT_MIN)
        if new_val > old_val:
            try: play_sfx("statsUp")
            except Exception: pass
        elif new_val < old_val:
            try: play_sfx("statsDown")
            except Exception: pass

    # ===== XP with new rules =====
    trait_for_xp = changed_attr if changed_attr else category
    # Pass along whether this was the Daily Double so shop effects can modify DD XP
    res = compute_xp_gain(trait_for_xp, category, item_text, pts, is_daily_double=is_daily_double)
    # compute_xp_gain now returns (final_xp, boost_delta, boost_pct)
    try:
        xp_gain, boost_delta, boost_pct = res
    except Exception:
        try:
            xp_gain, boost_delta = res
            boost_pct = 0
        except Exception:
            xp_gain = int(res)
            boost_delta = 0
            boost_pct = 0
    before_lvl = level_from_xp(get_total_xp())
    after_total = add_total_xp(xp_gain)
    after_lvl = level_from_xp(after_total)

    # Currency rewards for ATONE (small coin reward)
    try:
        if kind == "ATONE":
            # Assumption: award small coins proportional to points logged (20% of pts, min 1)
            coins_awarded = max(1, int(abs(pts) * 0.2))
            try:
                add_coins(coins_awarded)
            except Exception:
                pass
    except Exception:
        pass

    # Update UI and show boost delta on XP strip if available
    try:
        # refresh core data
        self.refresh_all()
        try:
            if hasattr(self, 'xpstrip'):
                if boost_delta:
                    # show +N XP in green
                    self.xpstrip.set_boost_info(f"+{boost_delta} XP")
                elif boost_pct:
                    # show percent if absolute delta rounds to 0
                    self.xpstrip.set_boost_info(f"+{boost_pct}%")
                else:
                    self.xpstrip.set_boost_info(None)
        except Exception:
            pass
    except Exception:
        pass

    if after_lvl > before_lvl:
        try: play_sfx("levelUp")
        except Exception: pass
        messagebox.showinfo("LEVEL UP!", f"You reached Level {after_lvl}!")
        try:
            # award coins for leveling up (10 coins per level)
            lvl_delta = max(0, after_lvl - before_lvl)
            if lvl_delta > 0:
                try: add_coins(10 * lvl_delta)
                except Exception: pass
            # every 5 levels grant a shard
            shards_now = after_lvl // 5
            shards_before = before_lvl // 5
            if shards_now > shards_before:
                try: add_shards(shards_now - shards_before)
                except Exception: pass
        except Exception:
            pass
