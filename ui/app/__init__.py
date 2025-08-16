# ui/app/__init__.py
# Orchestrates the UI + runs BaselineQuiz BEFORE any other UI loads

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta
import random
import calendar
import csv
from pathlib import Path

from .leveling import update_daily_emas_if_needed
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
from shop.currency import init as init_currency, add_coins, get_coins, get_coins_today, get_shards

# Components
from ..components.topbar import TopBar
from ..components.xp_strip import XPStrip
from ..components.stats import StatsPanel
from ..components.journal import JournalPanel
from ..components.logs import LogsPanel
from ..components.actions import ActionsBar
from ..components.dailydouble import DailyDoublePanel

# Split-out handlers
from .parts_actions import (
    save_journal as _save_journal,
    open_atone_dialog as _open_atone_dialog,
    open_sin_dialog as _open_sin_dialog,
)
from .parts_contracts import open_contracts as _open_contracts


# ---------------- Random challenge pool (CSV optional) ----------------
CHALLENGE_CSV = Path("data/random_challenges.csv")

def _load_challenge_pool_from_csv():
    if not CHALLENGE_CSV.exists():
        return None
    pool = []
    with CHALLENGE_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                title = row["title"].strip()
                trait = row["trait"].strip()
                minutes = int(row["minutes"])
                reward = int(row["reward_pts"])
                penalty = int(row["penalty_pts"])
            except Exception:
                continue
            pool.append((title, trait, minutes, reward, penalty))
    return pool or None


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

        # ======== RUN BASELINE QUIZ FIRST ========
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

        # Ensure we always have a first_day, even if quiz already done
        if not needs_quiz:
            start_iso = get_meta("start_day")
            if not start_iso:
                start_iso = date.today().isoformat()
                set_meta("start_day", start_iso)
            self.first_day = date.fromisoformat(start_iso)

        self.current_date = date.today()
        self.prev_stat_values = {t: STAT_MIN for t in POSITIVE_TRAITS}
        self.prev_xp_in_level = 0
        # currency init
        try:
            init_currency()
        except Exception:
            pass
        # For testing: seed large balance
        try:
            from shop.currency import set_coins_total, set_shards_total
            set_coins_total(10000)
            set_shards_total(5)
        except Exception:
            pass
        # track previous total xp for coin drip
        try:
            self._prev_total_xp = get_total_xp()
        except Exception:
            self._prev_total_xp = 0

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

    # ---------- Shop / Items UI ----------
    def show_items(self):
        # simple inventory viewer stored in data/shop_inventory.json
        import json
        inv_path = Path("data/shop_inventory.json")
        items = []
        if inv_path.exists():
            try:
                items = json.loads(inv_path.read_text(encoding="utf-8") or "[]")
            except Exception:
                items = []

        win = tk.Toplevel(self.root)
        win.title("Items")
        win.configure(bg=COLORS["BG"])
        win.geometry("420x320")
        win.grab_set()

        tk.Label(win, text="Owned Items", font=FONTS["h2"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(12,8))
        body = tk.Frame(win, bg=COLORS["CARD"])
        body.pack(fill="both", expand=True, padx=12, pady=8)

        if not items:
            tk.Label(body, text="No items owned.", bg=COLORS["CARD"], fg=COLORS["MUTED"]).pack(padx=8, pady=8)
        else:
            for it in items:
                tk.Label(body, text=it.get("item","?"), bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=8, pady=4)

    def _get_challenge_pool(self):
        # cache so we don’t re-read the file every click
        if not hasattr(self, "_challenge_pool_cache"):
            csv_pool = _load_challenge_pool_from_csv()
            if csv_pool:
                self._challenge_pool_cache = csv_pool
            else:
                # fallback to your current inline list
                self._challenge_pool_cache = [
                    ("Do 45 pushups",               "Physical", 30, 3, 2),
                    ("Go for a 1-hour walk",        "Physical", 60, 3, 2),
                    ("30 min deep work (no phone)", "Mindful",  30, 3, 2),
                    ("20 min meditation + journal", "Spiritual",30, 3, 2),
                    ("Read 20 pages",               "Intellect",40, 3, 2),
                    ("Call someone you care about", "Social",   10, 2, 1),
                    ("Complete a nagging chore",    "Integrity",25, 3, 2),
                ]
        return self._challenge_pool_cache

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
            on_next=self.go_next_day,
            on_calendar=self.open_calendar_popup,   # NEW
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
                on_today=self.go_to_today,                  
                on_random_challenge=self.open_random_challenge,
                on_logger=self.open_logger,
                on_items=self.show_items,
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
    

    # --- Calendar popup (only clickable on days that have entries) ---
    def open_calendar_popup(self):
        import calendar as _cal
        from datetime import date as _date

        first_day = getattr(self, "first_day", _date.today())
        today = _date.today()

        # We depend on this DB helper; fall back gracefully if missing.
        try:
            from database import get_logged_days_in_range
        except Exception:
            def get_logged_days_in_range(a, b):  # pragma: no cover
                return set()

        # Start from the month currently displayed in the app
        showing = _date(self.current_date.year, self.current_date.month, 1)

        # ---- Window shell ----
        win = tk.Toplevel(self.root)
        win.title("Pick a day")
        win.configure(bg=COLORS["BG"])
        win.geometry("380x360")
        win.grab_set()
        try:
            win.transient(self.root)
        except Exception:
            pass

        # ---- helpers ----
        def _month_bounds(d0: _date) -> tuple[_date, _date]:
            _, ndays = _cal.monthrange(d0.year, d0.month)
            first = _date(d0.year, d0.month, 1)
            last  = _date(d0.year, d0.month, ndays)
            if first < first_day: first = first_day
            if last > today: last = today
            return first, last

        def _tile(parent, text, *, enabled=False, on_click=None, is_today=False):
            """
            Small bordered tile that looks the same on all platforms.
            """
            wrap = tk.Frame(parent, bg=COLORS["BG"])
            wrap.pack(side="left", padx=3, pady=3)

            border_color = COLORS["CARD"] if not enabled else COLORS["PRIMARY"]
            brd = tk.Frame(
                wrap, bg=COLORS["BG"],
                highlightthickness=1 if enabled else 0,
                highlightbackground=border_color,
                highlightcolor=border_color,
                bd=0,
            )
            brd.pack()

            bg = COLORS["CARD"]
            fg = COLORS["MUTED"] if not enabled else COLORS["TEXT"]

            if is_today and enabled:
                # subtle ring to mark today
                brd.configure(highlightthickness=2, highlightbackground=COLORS["ACCENT"])

            lbl = tk.Label(
                brd, text=text, width=3,
                font=FONTS["body"], bg=bg, fg=fg,
                padx=8, pady=6,
            )
            lbl.pack()

            if enabled and on_click:
                def _hover(_e=None):
                    lbl.configure(bg=COLORS["PRIMARY"], fg=COLORS.get("PRIMARY_TEXT", COLORS["WHITE"]))
                    brd.configure(highlightbackground=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]))
                def _leave(_e=None):
                    lbl.configure(bg=bg, fg=COLORS["TEXT"])
                    brd.configure(highlightbackground=COLORS["PRIMARY"])
                for w in (brd, lbl):
                    w.bind("<Enter>", _hover)
                    w.bind("<Leave>", _leave)
                    w.bind("<Button-1>", lambda _e: on_click())
            return wrap

        # ---- Header ----
        header = tk.Frame(win, bg=COLORS["BG"]); header.pack(fill="x", pady=(8, 6))
        title_var = tk.StringVar()

        def _render_title():
            title_var.set(showing.strftime("%B %Y"))

        def _prev_month():
            nonlocal showing
            y, m = showing.year, showing.month
            y, m = (y - 1, 12) if m == 1 else (y, m - 1)
            # stop if entire month is before first_day
            if _date(y, m, _cal.monthrange(y, m)[1]) < first_day:
                return
            showing = _date(y, m, 1)
            _render_month()

        def _next_month():
            nonlocal showing
            y, m = showing.year, showing.month
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
            # stop if month would be after today's month
            if _date(y, m, 1) > _date(today.year, today.month, 1):
                return
            showing = _date(y, m, 1)
            _render_month()

        prev_b = RoundButton(
            header, "◀",
            fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["TEXT"], padx=10, pady=6, radius=12, command=_prev_month
        ); prev_b.pack(side="left", padx=8)

        tk.Label(header, textvariable=title_var, font=FONTS["h2"], bg=COLORS["BG"], fg=COLORS["TEXT"])\
            .pack(side="left", padx=8)

        next_b = RoundButton(
            header, "▶",
            fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["TEXT"], padx=10, pady=6, radius=12, command=_next_month
        ); next_b.pack(side="left", padx=8)

        # Weekday row
        wk = tk.Frame(win, bg=COLORS["BG"]); wk.pack(fill="x", pady=(0, 4))
        for wd in ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"):
            tk.Label(wk, text=wd, width=4, font=FONTS["small"], bg=COLORS["BG"], fg=COLORS["MUTED"])\
                .pack(side="left", padx=2)

        grid = tk.Frame(win, bg=COLORS["BG"]); grid.pack(fill="both", expand=True, padx=8, pady=4)

        # ---- Month grid ----
        def _render_month():
            for w in grid.winfo_children():
                w.destroy()
            _render_title()

            m_first, m_last = _month_bounds(showing)
            available = set()
            if m_first <= m_last:
                available = get_logged_days_in_range(m_first.isoformat(), m_last.isoformat())

            cal = _cal.Calendar(firstweekday=0)  # Monday = 0
            for week in cal.monthdayscalendar(showing.year, showing.month):
                row = tk.Frame(grid, bg=COLORS["BG"]); row.pack()
                for dnum in week:
                    if dnum == 0:
                        tk.Label(row, text="  ", width=4, bg=COLORS["BG"]).pack(side="left", padx=3, pady=3)
                        continue

                    d = _date(showing.year, showing.month, dnum)
                    in_window = first_day <= d <= today
                    d_iso = d.isoformat()
                    is_clickable = in_window and (d_iso in available)
                    is_today = (d == today)

                    if is_clickable:
                        def _jump(target=d):
                            self.current_date = target
                            self.refresh_all()
                            try: win.destroy()
                            except Exception: pass
                        _tile(row, f"{dnum}", enabled=True, on_click=_jump, is_today=is_today)
                    else:
                        _tile(row, f"{dnum}", enabled=False)

        _render_month()

    # ---------- Styles ----------
    def _apply_styles(self, style: ttk.Style):
        style.configure(
            "Treeview",
            background=COLORS["CARD"],
            fieldbackground=COLORS["CARD"],
            foreground=COLORS["TEXT"],
            rowheight=24,
        )
        style.configure(
            "Treeview.Heading",
            background=COLORS["PRIMARY"],
            foreground=COLORS.get("PRIMARY_TEXT", "#FFFFFF"),
        )
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

        # Baselines overlay
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
        try:
            # XP -> coin drip: 1 coin per 50 XP gained since last refresh
            prev = getattr(self, "_prev_total_xp", total)
            xp_delta = max(0, total - prev)
            if xp_delta >= 50:
                coins_to_award = xp_delta // 50
                # add_coins returns applied amount
                try:
                    added = add_coins(int(coins_to_award))
                except Exception:
                    added = 0
            self._prev_total_xp = total
        except Exception:
            pass
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
        # Update topbar currency display
        try:
            if hasattr(self, "topbar"):
                self.topbar.set_currency(get_coins(), get_shards())
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

    # --- TODAY JUMP ---
    def go_to_today(self):
        self.current_date = date.today()
        self.refresh_all()

    # --- RANDOM CHALLENGE ---
    def open_random_challenge(self):
        # Only for today
        if self.current_date != date.today():
            messagebox.showinfo("Random Challenge", "You can only start a challenge on today's page.")
            return

        # (title, trait, minutes, reward_pts, penalty_pts)
        pool = self._get_challenge_pool()
        title, trait, minutes, reward_pts, penalty_pts = random.choice(pool)

        # Daily Double multiplier (if today's atone matches)
        try:
            dd = get_daily_double(date.today().isoformat())
        except Exception:
            dd = None
        mult = 2 if dd and dd.get("atone") == trait else 1
        reward_pts_eff = reward_pts * mult
        penalty_pts_eff = penalty_pts * mult

        win = tk.Toplevel(self.root)
        win.title("Random Challenge")
        win.configure(bg=COLORS["BG"])
        win.geometry("420x260")
        win.grab_set()
        try:
            win.transient(self.root)
        except Exception:
            pass

        tk.Label(win, text="Random Challenge", font=FONTS["h2"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(12, 8))
        tk.Label(win, text=title, font=FONTS["h3"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(0, 6))
        tk.Label(
            win, text=f"Trait: {trait}  •  Duration: {minutes} min",
            font=FONTS["small"], bg=COLORS["BG"], fg=COLORS["MUTED"]
        ).pack(pady=(0, 8))

        timer_lbl = tk.Label(
            win, text=f"{minutes:02d}:00", font=("Helvetica", 18, "bold"),
            bg=COLORS["BG"], fg=COLORS["PRIMARY"]
        )
        timer_lbl.pack(pady=(4, 10))

        btn_row = tk.Frame(win, bg=COLORS["BG"])
        btn_row.pack(pady=8)

        # State for countdown
        seconds_left = minutes * 60
        ticking_id = {"id": None}
        running = {"started": False, "finished": False}

        def fmt(sec):
            m, s = divmod(max(0, sec), 60)
            return f"{int(m):02d}:{int(s):02d}"

        def stop_timer():
            _id = ticking_id["id"]
            if _id is not None:
                try:
                    win.after_cancel(_id)
                except Exception:
                    pass
                ticking_id["id"] = None

        def tick():
            if running["finished"]:
                return
            nonlocal seconds_left
            seconds_left -= 1
            timer_lbl.config(text=fmt(seconds_left))
            if seconds_left <= 0:
                # Auto-fail
                return on_fail(auto=True)
            ticking_id["id"] = win.after(1000, tick)

        def on_accept():
            if running["started"]:
                return
            running["started"] = True
            # Swap buttons to Complete / Give Up
            for w in btn_row.winfo_children():
                w.destroy()
            RoundButton(
                btn_row, "Complete",
                fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS.get("PRIMARY_TEXT", COLORS["WHITE"]),
                padx=16, pady=10, radius=14, command=on_complete
            ).pack(side="left", padx=8)
            RoundButton(
                btn_row, "Give Up",
                fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
                fg=COLORS.get("ACCENT_TEXT", COLORS["WHITE"]),
                padx=16, pady=10, radius=14, command=on_fail
            ).pack(side="left", padx=8)
            # Start countdown
            timer_lbl.config(text=fmt(seconds_left))
            ticking_id["id"] = win.after(1000, tick)

        def on_decline():
            stop_timer()
            win.destroy()

        def on_complete():
            if running["finished"]:
                return
            running["finished"] = True
            stop_timer()

            # Record success as an ATONE on the mapped trait
            today_iso = date.today().isoformat()
            try:
                insert_entry(today_iso, "ATONE", trait, f"Challenge: {title}", reward_pts_eff)
                update_attribute_score(trait, reward_pts_eff)
            except Exception:
                pass

            # XP
            try:
                before = level_from_xp(get_total_xp())
                after_total = add_total_xp(reward_pts_eff * 10)
                after = level_from_xp(after_total)
                if after > before:
                    try:
                        play_sfx("levelUp")
                    except Exception:
                        pass
            except Exception:
                pass

            # SFX positive
            try:
                play_sfx("statsUp")
            except Exception:
                pass

            self.refresh_all()
            messagebox.showinfo("Challenge", "Completed! Nice work.")
            win.destroy()

        def on_fail(auto: bool = False):
            if running["finished"]:
                return
            running["finished"] = True
            stop_timer()

            today_iso = date.today().isoformat()
            try:
                # Log as a fail; decrement same trait to keep it intuitive
                insert_entry(today_iso, "SIN", f"Challenge fail ({trait})", f"Failed: {title}", -penalty_pts_eff)
                update_attribute_score(trait, -penalty_pts_eff)
            except Exception:
                pass

            # XP penalty
            try:
                add_total_xp(-penalty_pts_eff * 10)
            except Exception:
                pass

            # SFX negative
            try:
                play_sfx("statsDown")
            except Exception:
                pass

            self.refresh_all()
            message = "Time's up — challenge failed." if auto else "Challenge failed."
            messagebox.showinfo("Challenge", message)
            win.destroy()

        # Initial buttons (Accept / Decline)
        RoundButton(
            btn_row, "Accept",
            fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS.get("PRIMARY_TEXT", COLORS["WHITE"]),
            padx=16, pady=10, radius=14, command=on_accept
        ).pack(side="left", padx=8)
        RoundButton(
            btn_row, "Decline",
            fill=COLORS["CARD"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
            fg=COLORS["TEXT"], padx=16, pady=10, radius=14, command=on_decline
        ).pack(side="left", padx=8)

        # Clean up timer if window is closed
        def _on_close():
            stop_timer()
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_close)

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

        RoundButton(
            win, "Apply Theme",
            fill=COLORS["PRIMARY"],
            hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS.get("PRIMARY_TEXT", COLORS["WHITE"]),
            padx=16, pady=8, radius=12,
            command=apply_and_close
        ).pack(pady=14)

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
