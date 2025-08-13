# Orchestrates the UI by composing small components + Theme switcher + SFX + BGM shuffle
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta
import random

from sound import play_sfx
from sound import init as init_sound

# BGM shuffle
from bgm import init_bgm, start_bgm_shuffle, stop_bgm

# App constants / data
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
    # new features
    set_daily_double, get_daily_double, get_active_contracts,
    create_contract, mark_contract_broken, mark_contract_penalty_applied,
    get_baselines,
)
from prompts import get_prompt_for_date
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
from .components.dailydouble import DailyDoublePanel   # NEW
from .dialogs import ask_action  # returns (category, item_text, pts) or None


class HabitTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Habit Tracker — Solo Level-Up")

        # Init audio backends
        init_sound()
        init_bgm()

        # Load saved theme BEFORE building UI
        saved_theme = get_meta("theme")
        if saved_theme and saved_theme in PALETTES:
            set_theme(saved_theme)

        # Start size/position (user can still resize)
        self.root.geometry("1544x890+5+43")
        self.root.configure(bg=COLORS["BG"])

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self._apply_styles(style)

        # First-run quiz
        if get_meta("quiz_done") != "1":
            q = BaselineQuiz(self.root)
            self.root.wait_window(q)

        self.current_date = date.today()
        self.prev_stat_values = {t: STAT_MIN for t in POSITIVE_TRAITS}
        self.prev_xp_in_level = 0

        self._build_ui()
        self.refresh_all(first=True)

        # Start background music shuffle (looks for bgmusic.mp3, bgmusic2.mp3, bgmusic3.mp3)
        start_bgm_shuffle(volume=0.22, crossfade_ms=700)

        # Clean shutdown so music thread stops
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # handy shortcut (optional): open contracts with Ctrl+Shift+C
        self.root.bind("<Control-Shift-C>", lambda e: self.open_contracts())

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

        # NEW: Daily Double panel under Journal
        self.dd_panel = DailyDoublePanel(left)
        self.dd_panel.pack(side="top", fill="x", padx=4, pady=(0, 8))

        # Right column
        right = tk.Frame(grid, bg=COLORS["BG"])
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self.logs = LogsPanel(right)
        self.logs.pack(fill="both", expand=True, padx=4, pady=0)

        # Bottom actions (Theme button; Contracts if supported by your ActionsBar)
        try:
            self.actions = ActionsBar(
                self.root,
                on_atone=self.open_atone_dialog,
                on_sin=self.open_sin_dialog,
                on_theme=self.open_theme_picker,
                on_contracts=self.open_contracts,   # works if your ActionsBar supports it
            )
        except TypeError:
            # fallback for older ActionsBar signature
            self.actions = ActionsBar(
                self.root,
                on_atone=self.open_atone_dialog,
                on_sin=self.open_sin_dialog,
                on_theme=self.open_theme_picker,
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
                        troughcolor="#D4D4D8",
                        background=COLORS["ACCENT"])

    # ---------- Refresh ----------
    def refresh_all(self, first=False):
        # Date + today lock
        is_today = (self.current_date == date.today())
        self.topbar.set_date(self.current_date, is_today)

        # Baselines → stats (for green/red delta overlay)
        try:
            self.stats.set_baselines(get_baselines())
        except Exception:
            pass  # in case you're still on the old StatsPanel

        # Stats values
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

        # Journal + prompt
        day = self.current_date.isoformat()
        content = get_journal(day) or ""
        self.journal.set_text(content, editable=is_today)
        try:
            self.journal.set_prompt(get_prompt_for_date(day))
        except Exception:
            pass

        # Daily Double: ensure today's pick exists and display it
        dd = get_daily_double(day)
        if not dd:
            dd = {"atone": random.choice(POSITIVE_TRAITS), "sin": random.choice(SINS)}
            set_daily_double(day, dd["atone"], dd["sin"])
        self.dd_panel.set_values(dd["atone"], dd["sin"])

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

        category, item_text, pts = result  # pts positive for ATONE, negative for SIN as set by dialog

        # Daily Double multiplier
        dd = get_daily_double(self.current_date.isoformat())
        if dd:
            if kind == "ATONE" and category == dd["atone"]:
                pts *= 2
            elif kind == "SIN" and category == dd["sin"]:
                pts *= 2  # remains negative, doubles magnitude

        # Which attribute changes? (SIN maps to a positive trait)
        changed_attr = category if kind == "ATONE" else SIN_TO_ATTRIBUTE.get(category)

        # Capture old value to detect delta for SFX
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

        # Apply stat change
        if kind == "ATONE":
            update_attribute_score(category, abs(pts))
        else:
            if changed_attr:
                update_attribute_score(changed_attr, pts)

        # SFX: stat up/down (only if value actually changed)
        if changed_attr is not None and old_val is not None:
            new_val = get_attributes().get(changed_attr, {}).get("score", STAT_MIN)
            if new_val > old_val:
                play_sfx("statsUp")
            elif new_val < old_val:
                play_sfx("statsDown")

        # XP + level-up SFX
        before = level_from_xp(get_total_xp())
        after_total = add_total_xp(pts * 10)
        after = level_from_xp(after_total)
        self.refresh_all()
        if after > before:
            play_sfx("levelUp")
            messagebox.showinfo("LEVEL UP!", f"You reached Level {after}!")

    # ---------- Theme picker ----------
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
        # Destroy current UI and rebuild with new COLORS
        for w in self.root.winfo_children():
            w.destroy()

        self.root.configure(bg=COLORS["BG"])

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        self._apply_styles(style)

        # Rebuild widgets and refresh current state
        self._build_ui()
        self.refresh_all(first=False)

    # ---------- Contracts ----------
    def open_contracts(self):
        win = tk.Toplevel(self.root)
        win.title("Contracts (7-day pacts)")
        win.configure(bg=COLORS["BG"])
        win.geometry("520x360")
        win.grab_set()

        tk.Label(win, text="Active Contracts", font=FONTS["h3"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(10,4))

        frame = tk.Frame(win, bg=COLORS["BG"]); frame.pack(fill="both", expand=True, padx=12, pady=8)
        listbox = tk.Listbox(frame, height=8)
        listbox.pack(fill="both", expand=True, side="left")
        sb = tk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        sb.pack(side="right", fill="y"); listbox.configure(yscrollcommand=sb.set)

        def refresh():
            listbox.delete(0, "end")
            for c in get_active_contracts(date.today().isoformat()):
                status = "BROKEN" if c["broken"] else "ACTIVE"
                listbox.insert("end", f'#{c["id"]} {c["title"]} ({c["start_date"]} → {c["end_date"]}) [{status}] Penalty:{c["penalty_xp"]}')

        refresh()

        # Create new contract
        tk.Label(win, text="Create new (7 days):", bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(anchor="w", padx=12, pady=(8,2))
        entry = tk.Entry(win); entry.pack(fill="x", padx=12)

        def create():
            title = entry.get().strip()
            if not title: return
            start = date.today()
            end = start + timedelta(days=6)
            create_contract(title=title, penalty_xp=200, start_iso=start.isoformat(), end_iso=end.isoformat())
            entry.delete(0,"end"); refresh()

        RoundButton(win, "Create Pact",
                    fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                    fg=COLORS["WHITE"], padx=14, pady=8, radius=12, command=create).pack(pady=6)

        def break_selected():
            sel = listbox.curselection()
            if not sel: return
            line = listbox.get(sel[0])
            try:
                cid = int(line.split()[0].lstrip("#"))
            except Exception:
                return
            # apply one-time penalty if not already applied
            for c in get_active_contracts(date.today().isoformat()):
                if c["id"] == cid:
                    mark_contract_broken(cid)
                    if not c["penalty_applied"]:
                        add_total_xp(-abs(int(c["penalty_xp"])) * 10)
                        mark_contract_penalty_applied(cid)
                    break
            refresh()
            self.refresh_all()

        RoundButton(win, "Mark Broken (apply penalty once)",
                    fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
                    fg=COLORS["WHITE"], padx=14, pady=8, radius=12, command=break_selected).pack(pady=6)

    # ---------- Cleanup ----------
    def _on_close(self):
        try:
            stop_bgm()
        finally:
            self.root.destroy()
