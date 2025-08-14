# ui/app/__init__.py
# Orchestrates the UI + runs BaselineQuiz BEFORE any other UI loads

import tkinter as tk
from .leveling import update_daily_emas_if_needed
from tkinter import ttk, messagebox
from datetime import date, timedelta
import random
from .parts_logger import open_logger as _open_logger


from sound import play_sfx, init as init_sound, set_muted
from bgm import init_bgm, start_bgm_shuffle, stop_bgm

from constants import (
    COLORS, FONTS, POSITIVE_TRAITS, SINS,
    SIN_TO_ATTRIBUTE, STAT_MIN, STAT_MAX,
    ATONE_MENU, SIN_MENU,
    PALETTES, set_theme
)
from database import (
    get_meta, set_meta,
    get_attributes, update_attribute_score,
    insert_entry, get_entries_by_date, get_journal, upsert_journal,
    set_daily_double, get_daily_double,
    create_personal_contract_limited,
    get_baselines,
    get_available_contracts, claim_contract_offer,
    get_active_contracts_count, get_personal_active_count, get_available_offers_count,
    generate_daily_contracts_if_needed,
    mark_contract_broken, mark_contract_penalty_applied,
)
from prompts import get_prompt_for_date
from exp_system import (
    xp_to_next, level_from_xp, xp_in_level,
    get_total_xp, add_total_xp, average_stat, compute_rank
)
from widgets import RoundButton
from quiz import BaselineQuiz

# Components
from ..components.topbar import TopBar
from ..components.xp_strip import XPStrip
from ..components.stats import StatsPanel
from ..components.journal import JournalPanel
from ..components.logs import LogsPanel
from ..components.actions import ActionsBar
from ..components.dailydouble import DailyDoublePanel

# Split-out handlers
from .parts_actions import save_journal as _save_journal, open_atone_dialog as _open_atone_dialog, open_sin_dialog as _open_sin_dialog
from .parts_contracts import open_contracts as _open_contracts


class HabitTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Habit Tracker — Solo Level-Up")

        # Init audio backends
        init_sound()
        init_bgm()

        # Theme + sound state first
        saved_theme = get_meta("theme")
        if saved_theme and saved_theme in PALETTES:
            set_theme(saved_theme)

        muted_flag = (get_meta("sound_muted") == "1")
        self.sound_enabled = not muted_flag
        set_muted(muted_flag)

        # Prepare root but DO NOT build UI yet
        self.root.geometry("1544x890+5+43")
        self.root.configure(bg=COLORS["BG"])
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self._apply_styles(style)

            # ======== RUN BASELINE QUIZ FIRST (no withdraw) ========
        needs_quiz = (get_meta("quiz_done") != "1")

        # Make sure the main window is visible
        self.root.deiconify()
        self.root.update_idletasks()

        if needs_quiz:
            q = BaselineQuiz(self.root)  # should be a Toplevel
            try:
                q.transient(self.root)   # tie to main window
                q.grab_set()             # modal
                q.focus_force()
                q.lift()
                q.attributes("-topmost", True)
                q.after(150, lambda: q.attributes("-topmost", False))
            except Exception:
                pass

            # Block until quiz closes
            self.root.wait_window(q)
            # --- Establish the earliest day the user can view ---
            start_iso = get_meta("start_day")
            if not start_iso:
                # Use *today* as the start day the moment the quiz completes
                start_iso = date.today().isoformat()
                set_meta("start_day", start_iso)
            self.first_day = date.fromisoformat(start_iso)

        # =========================================
        # --- Ensure we always have a first_day, even if quiz already done ---
        if needs_quiz:
            # you already have this part that sets start_day and self.first_day
            start_iso = get_meta("start_day")
            if not start_iso:
                start_iso = date.today().isoformat()
                set_meta("start_day", start_iso)
            self.first_day = date.fromisoformat(start_iso)
        else:
            # Quiz already completed earlier → load or create start_day now
            start_iso = get_meta("start_day")
            if not start_iso:
                start_iso = date.today().isoformat()
                set_meta("start_day", start_iso)
            self.first_day = date.fromisoformat(start_iso)


        self.current_date = date.today()
        self.prev_stat_values = {t: STAT_MIN for t in POSITIVE_TRAITS}
        self.prev_xp_in_level = 0

        # Now build the rest of the UI
        self._build_ui()
        self.refresh_all(first=True)

        # Start BGM only after quiz is done
        if self.sound_enabled:
            start_bgm_shuffle(volume=0.22, crossfade_ms=700)

        # Clean shutdown so music thread stops
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Shortcuts
        self.root.bind("<Control-Shift-C>", lambda e: self.open_contracts())
        self.root.bind("<Control-m>", lambda e: self.toggle_sound())
        self.root.bind("<Control-M>", lambda e: self.toggle_sound())

        try:
            self.actions.set_sound_state(self.sound_enabled)
        except Exception:
            pass
    
    def _clamp_to_allowed_range(self, d: date) -> date:
        today = date.today()
        if d < self.first_day:
            return self.first_day
        if d > today:
            return today
        return d

    def _update_nav_buttons(self):
        """If TopBar supports it, reflect the allowed range in button state."""
        try:
            prev_ok = self.current_date > self.first_day
            next_ok = self.current_date < date.today()
            # Try common APIs your TopBar might have:
            if hasattr(self.topbar, "set_nav_enabled"):
                self.topbar.set_nav_enabled(prev_ok, next_ok)
            else:
                if hasattr(self.topbar, "set_prev_enabled"):
                    self.topbar.set_prev_enabled(prev_ok)
                if hasattr(self.topbar, "set_next_enabled"):
                    self.topbar.set_next_enabled(next_ok)
        except Exception:
            pass


    # ---------- Build ----------
    def _build_ui(self):
        self.topbar = TopBar(
            master=self.root,
            on_prev=self.go_prev_day,
            on_next=self.go_next_day
        )
        self.topbar.pack(fill="x", pady=(12, 6))

        self.xpstrip = XPStrip(self.root)
        self.xpstrip.pack(fill="x", pady=(0, 10))

        grid = tk.Frame(self.root, bg=COLORS["BG"])
        grid.pack(fill="both", expand=True, padx=12, pady=8)

        left = tk.Frame(grid, bg=COLORS["BG"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self.stats = StatsPanel(left)
        self.stats.pack(side="top", fill="x", padx=4, pady=(0, 8))

        self.journal = JournalPanel(left, on_save=self.save_journal)
        self.journal.pack(side="top", fill="both", expand=True, padx=4, pady=(0, 4))

        self.dd_panel = DailyDoublePanel(left)
        self.dd_panel.pack(side="top", fill="x", padx=4, pady=(0, 8))

        right = tk.Frame(grid, bg=COLORS["BG"])
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self.logs = LogsPanel(right)
        self.logs.pack(fill="both", expand=True, padx=4, pady=0)

        try:
            self.actions = ActionsBar(
            self.root,
            on_atone=self.open_atone_dialog,
            on_sin=self.open_sin_dialog,
            on_theme=self.open_theme_picker,
            on_contracts=self.open_contracts,
            on_faq=None,
            on_sound_toggle=self.toggle_sound,
            on_logger=self.open_logger,   # <-- NEW
        )
        except TypeError:
            self.actions = ActionsBar(
                self.root,
                on_atone=self.open_atone_dialog,
                on_sin=self.open_sin_dialog,
                on_theme=self.open_theme_picker,
                on_contracts=self.open_contracts,
            )
        self.actions.pack(fill="x", pady=10)

    # ---------- Styles ----------
    def _apply_styles(self, style: ttk.Style):
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
                        troughcolor=COLORS.get("TRACK", "#D4D4D8"),
                        background=COLORS["ACCENT"])

    # ---------- Helpers ----------
    def _ensure_offers_today(self, min_count: int = 3):
        try:
            if generate_daily_contracts_if_needed:
                generate_daily_contracts_if_needed()
            if get_available_offers_count() < min_count:
                set_meta("offers_day", "")
                if generate_daily_contracts_if_needed:
                    generate_daily_contracts_if_needed()
        except Exception:
            pass

    # ---------- Refresh ----------
    def refresh_all(self, first=False):
        
        self.current_date = self._clamp_to_allowed_range(self.current_date)
        is_today = (self.current_date == date.today())
        self.topbar.set_date(self.current_date, is_today)
        self._update_nav_buttons()

        if is_today:
            self._ensure_offers_today()

        # Ensure EMA baselines are updated once per day from current scores
        try:
            update_daily_emas_if_needed()
        except Exception:
            pass

        # Baselines → stats overlay (now uses updated attributes.baseline)
        try:
            from database import get_baselines
            self.stats.set_baselines(get_baselines())
        except Exception:
            pass

        
        try:
            self.stats.set_baselines(get_baselines())
        except Exception:
            pass

        stats = get_attributes()
        for trait in POSITIVE_TRAITS:
            new_val = stats.get(trait, {}).get("score", STAT_MIN)
            old_val = self.prev_stat_values.get(trait, STAT_MIN)
            self.stats.set_value(trait, old_val, new_val)
            self.prev_stat_values[trait] = new_val

        avg = average_stat({t: stats.get(t, {}).get("score", STAT_MIN) for t in POSITIVE_TRAITS})
        self.topbar.set_rank(f"Rank: {compute_rank(avg)}  •  Avg {avg}")

        records = get_entries_by_date(self.current_date.isoformat())
        self.logs.load(records)

        day = self.current_date.isoformat()
        content = get_journal(day) or ""
        self.journal.set_text(content, editable=is_today)
        try:
            self.journal.set_prompt(get_prompt_for_date(day))
        except Exception:
            pass

        dd = get_daily_double(day)
        if not dd:
            dd = {"atone": random.choice(POSITIVE_TRAITS), "sin": random.choice(SINS)}
            set_daily_double(day, dd["atone"], dd["sin"])
        self.dd_panel.set_values(dd["atone"], dd["sin"])

        self.actions.enable(is_today)

        total = get_total_xp()
        lvl = level_from_xp(total)
        in_lvl = xp_in_level(total, lvl)
        need = xp_to_next(lvl)
        self.xpstrip.set_level(lvl, in_lvl, need, animate_from=(0 if first else self.prev_xp_in_level))
        self.prev_xp_in_level = in_lvl

        try:
            self.actions.set_contracts_badge(get_available_offers_count())
        except Exception:
            pass
        try:
            self.actions.set_sound_state(self.sound_enabled)
        except Exception:
            pass

    # ---------- Sound ----------
    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        muted = (not self.sound_enabled)
        set_meta("sound_muted", "1" if muted else "0")
        try:
            set_muted(muted)
        except Exception:
            pass
        try:
            if muted:
                stop_bgm()
            else:
                start_bgm_shuffle(volume=0.22, crossfade_ms=700)
        except Exception:
            pass
        try:
            self.actions.set_sound_state(self.sound_enabled)
        except Exception:
            pass

    # ---------- Nav ----------
    def go_prev_day(self):
        if self.current_date <= self.first_day:
            return
        self.current_date -= timedelta(days=1)
        self.refresh_all()

    def go_next_day(self):
        if self.current_date >= date.today():
            return
        self.current_date += timedelta(days=1)
        self.refresh_all()

    # ---------- Delegates to split parts ----------
    def open_logger(self):
        return _open_logger(self)
    
    def save_journal(self, text: str):
        return _save_journal(self, text)

    def open_atone_dialog(self):
        return _open_atone_dialog(self)

    def open_sin_dialog(self):
        return _open_sin_dialog(self)

    def open_contracts(self):
        return _open_contracts(self)

    # ---------- Theme ----------
    def open_theme_picker(self):
        win = tk.Toplevel(self.root)
        win.title("Choose Theme")
        win.configure(bg=COLORS["BG"])
        win.geometry("360x210")
        win.grab_set()

        tk.Label(win, text="Theme", font=("Helvetica", 14, "bold"),
                 bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(12, 6))

        names = list(PALETTES.keys())
        current = get_meta("theme") or names[0]
        var = tk.StringVar(value=current)

        cb = ttk.Combobox(win, values=names, textvariable=var, state="readonly", width=28)
        cb.pack(pady=8)

        def apply_and_close():
            name = var.get()
            if name not in PALETTES:
                return
            set_theme(name)
            set_meta("theme", name)
            self._rebuild_ui()
            win.destroy()

        RoundButton(win, "Apply Theme",
                    fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                    fg=COLORS["WHITE"], padx=16, pady=8, radius=12,
                    command=apply_and_close).pack(pady=14)

    def _rebuild_ui(self):
        for w in self.root.winfo_children():
            w.destroy()
        self.root.configure(bg=COLORS["BG"])
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self._apply_styles(style)
        self._build_ui()
        self.refresh_all(first=False)

    # ---------- Cleanup ----------
    def _on_close(self):
        try:
            stop_bgm()
        finally:
            self.root.destroy()
