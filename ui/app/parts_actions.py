from tkinter import messagebox
import random
from constants import POSITIVE_TRAITS, SINS, SIN_TO_ATTRIBUTE
from database import (
    get_attributes, insert_entry, update_attribute_score,
    get_daily_double, get_journal, upsert_journal
)
from exp_system import (
    level_from_xp, get_total_xp, add_total_xp
)
from animations import flash_widget
from sound import play_sfx
# FIX: dialogs is in ui/dialogs.py, so go up one package
from ..dialogs import ask_action


def save_journal(self, text: str):
    from datetime import date
    if self.current_date != date.today():
        return
    upsert_journal(self.current_date.isoformat(), text.strip())
    self.journal.note_saved()
    try:
        flash_widget(self.journal.status_label, times=2, on="#C7F9CC")
    except Exception:
        pass


def open_atone_dialog(self):
    handle_action(self, kind="ATONE")


def open_sin_dialog(self):
    handle_action(self, kind="SIN")


def handle_action(self, kind: str):
    from datetime import date
    from constants import STAT_MIN, ATONE_MENU, SIN_MENU

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

    category, item_text, pts = result  # pts positive for ATONE, negative for SIN

    # Daily Double
    dd = get_daily_double(self.current_date.isoformat())
    if dd:
        if kind == "ATONE" and category == dd["atone"]:
            pts *= 2
        elif kind == "SIN" and category == dd["sin"]:
            pts *= 2  # stays negative

    # Which attribute changes?
    changed_attr = category if kind == "ATONE" else SIN_TO_ATTRIBUTE.get(category)

    # Old value to detect delta for SFX
    old_val = None
    if changed_attr:
        old_val = get_attributes().get(changed_attr, {}).get("score", 35)

    # Save entry
    insert_entry(
        date=self.current_date.isoformat(),
        entry_type=kind,
        category=category,
        item=item_text,
        points=pts
    )

    # Apply stat change
    if kind == "ATONE":
        update_attribute_score(category, abs(pts))
    else:
        if changed_attr:
            update_attribute_score(changed_attr, pts)

    # SFX
    if changed_attr is not None and old_val is not None:
        new_val = get_attributes().get(changed_attr, {}).get("score", 35)
        if new_val > old_val:
            try: play_sfx("statsUp")
            except Exception: pass
        elif new_val < old_val:
            try: play_sfx("statsDown")
            except Exception: pass

    # XP + level-up
    before = level_from_xp(get_total_xp())
    after_total = add_total_xp(pts * 10)
    after = level_from_xp(after_total)
    self.refresh_all()
    if after > before:
        try: play_sfx("levelUp")
        except Exception: pass
        messagebox.showinfo("LEVEL UP!", f"You reached Level {after}!")
