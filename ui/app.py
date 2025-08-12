# Orchestrates the UI by composing small components

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta

from constants import (
    COLORS, FONTS, POSITIVE_TRAITS, SINS,
    SIN_TO_ATTRIBUTE, STAT_MIN, STAT_MAX,
    ATONE_MENU, SIN_MENU
)
from database import (
    get_meta, get_attributes, update_attribute_score,
    insert_entry, get_entries_by_date, get_journal, upsert_journal
)
from exp_system import (
    xp_to_next, level_from_xp, xp_in_level,
    get_total_xp, add_total_xp, average_stat, compute_rank
)
from animations import animate_intvar, flash_widget
from widgets import RoundButton
from quiz import BaselineQuiz

# Components
from .components.topbar import TopBar
from .components.xp_strip import XPStrip
from .components.stats import StatsPanel
from .components.journal import JournalPanel
from .components.logs import LogsPanel
from .components.actions import ActionsBar
from .dialogs import ask_action  # returns (category, item_text, pts) or None


class HabitTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Habit Tracker — Solo Level-Up")
        self.root.geometry("1024x840")
        self.root.configure(bg=COLORS["BG"])

        style = ttk.Style()
        try: style.theme_use("clam")
        except tk.TclError: pass

        style.configure("Treeview",
                        background=COLORS["CARD"],
                        fieldbackground=COLORS["CARD"],
                        foreground=COLORS["TEXT"],
                        rowheight=24)
        style.configure("Treeview.Heading",
                        background=COLORS["PRIMARY"],
                        foreground=COLORS["WHITE"])
        style.configure("XP.Horizontal.TProgressbar",
                        troughcolor=COLORS["CARD"],
                        background=COLORS["PRIMARY"])
        style.configure("Stat.Horizontal.TProgressbar",
                        troughcolor="#D4D4D8",
                        background=COLORS["ACCENT"])

        # First-run quiz
        if get_meta("quiz_done") != "1":
            q = BaselineQuiz(self.root)
            self.root.wait_window(q)

        self.current_date = date.today()
        self.prev_stat_values = {t: STAT_MIN for t in POSITIVE_TRAITS}
        self.prev_xp_in_level = 0

        self._build_ui()
        self.refresh_all(first=True)

    # ---------- Build ----------
    def _build_ui(self):
        # Header
        self.topbar = TopBar(
            master=self.root,
            on_prev=self.go_prev_day,
            on_next=self.go_next_day
        )
        self.topbar.pack(fill="x", pady=(12, 6))

        self.xpstrip = XPStrip(self.root)
        self.xpstrip.pack(fill="x", pady=(0, 10))

        # Main grid
        grid = tk.Frame(self.root, bg=COLORS["BG"])
        grid.pack(fill="both", expand=True, padx=12, pady=8)

        # Left column
        left = tk.Frame(grid, bg=COLORS["BG"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.stats = StatsPanel(left)
        self.stats.pack(side="top", fill="x", padx=4, pady=(0, 8))

        self.journal = JournalPanel(left, on_save=self.save_journal)
        self.journal.pack(side="top", fill="both", expand=True, padx=4, pady=(0, 4))

        # Right column
        right = tk.Frame(grid, bg=COLORS["BG"])
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self.logs = LogsPanel(right)
        self.logs.pack(fill="both", expand=True, padx=4, pady=0)

        # Bottom actions
        self.actions = ActionsBar(
            self.root,
            on_atone=self.open_atone_dialog,
            on_sin=self.open_sin_dialog
        )
        self.actions.pack(fill="x", pady=10)

    # ---------- Refresh ----------
    def refresh_all(self, first=False):
        # Date + today lock
        is_today = (self.current_date == date.today())
        self.topbar.set_date(self.current_date, is_today)

        # Stats
        stats = get_attributes()
        for trait in POSITIVE_TRAITS:
            new_val = stats.get(trait, {}).get("score", STAT_MIN)
            old_val = self.prev_stat_values.get(trait, STAT_MIN)
            self.stats.set_value(trait, old_val, new_val)
            self.prev_stat_values[trait] = new_val

        avg = average_stat({t: stats.get(t, {}).get("score", STAT_MIN) for t in POSITIVE_TRAITS})
        self.topbar.set_rank(f"Rank: {compute_rank(avg)}  •  Avg {avg}")

        # Entries
        records = get_entries_by_date(self.current_date.isoformat())
        self.logs.load(records)

        # Journal
        content = get_journal(self.current_date.isoformat()) or ""
        self.journal.set_text(content, editable=is_today)

        # Buttons lock
        self.actions.enable(is_today)

        # XP
        total = get_total_xp()
        lvl = level_from_xp(total)
        in_lvl = xp_in_level(total, lvl)
        need = xp_to_next(lvl)
        self.xpstrip.set_level(lvl, in_lvl, need, animate_from=(0 if first else self.prev_xp_in_level))
        self.prev_xp_in_level = in_lvl

    # ---------- Nav ----------
    def go_prev_day(self):
        self.current_date -= timedelta(days=1)
        self.refresh_all()

    def go_next_day(self):
        self.current_date += timedelta(days=1)
        self.refresh_all()

    # ---------- Journal ----------
    def save_journal(self, text: str):
        if self.current_date != date.today():
            return
        upsert_journal(self.current_date.isoformat(), text.strip())
        self.journal.note_saved()
        flash_widget(self.journal.status_label, times=2, on="#C7F9CC")

    # ---------- Action dialogs ----------
    def open_atone_dialog(self):
        self._handle_action(kind="ATONE")

    def open_sin_dialog(self):
        self._handle_action(kind="SIN")

    def _handle_action(self, kind: str):
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

        category, item_text, pts = result  # pts can be negative for SIN

        # Save entry
        insert_entry(
            date=self.current_date.isoformat(),
            entry_type=kind,
            category=category,
            item=item_text,
            points=pts
        )

        # Attribute adjustments
        if kind == "ATONE":
            update_attribute_score(category, abs(pts))
        else:
            target = SIN_TO_ATTRIBUTE.get(category)
            if target:
                update_attribute_score(target, pts)

        # XP and level-up
        before = level_from_xp(get_total_xp())
        after_total = add_total_xp(pts * 10)
        after = level_from_xp(after_total)
        self.refresh_all()
        if after > before:
            messagebox.showinfo("LEVEL UP!", f"You reached Level {after}!")
