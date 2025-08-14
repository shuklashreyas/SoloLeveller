# Orchestrates the UI by composing small components + Theme switcher + SFX + BGM shuffle + Mute toggle

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, timedelta
import random

from sound import play_sfx, init as init_sound, set_muted

# BGM shuffle (fixed trailing comma)
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
    set_daily_double, get_daily_double,
    # Personal with limits
    create_personal_contract_limited,
    get_baselines,
    # Offers / limits
    get_available_contracts, claim_contract_offer,
    get_active_contracts_count, get_personal_active_count, get_available_offers_count,
    # Daily offers seeder
    generate_daily_contracts_if_needed,
    # For penalties
    mark_contract_broken, mark_contract_penalty_applied,
    # If your DB exposes this; otherwise guard usage in UI.
    # get_active_contracts,   # ← uncomment if you have it
)

from prompts import get_prompt_for_date
from exp_system import (
    xp_to_next, level_from_xp, xp_in_level,
    get_total_xp, add_total_xp, average_stat, compute_rank
)
from animations import flash_widget
from widgets import RoundButton
from quiz import BaselineQuiz

# Components
from .components.topbar import TopBar
from .components.xp_strip import XPStrip
from .components.stats import StatsPanel
from .components.journal import JournalPanel
from .components.logs import LogsPanel
from .components.actions import ActionsBar
from .components.dailydouble import DailyDoublePanel
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

        # Load saved mute state (default: sound ON)
        muted_flag = (get_meta("sound_muted") == "1")
        self.sound_enabled = not muted_flag
        set_muted(muted_flag)

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

        # Start background music shuffle only if sound is enabled
        if self.sound_enabled:
            start_bgm_shuffle(volume=0.22, crossfade_ms=700)

        # Clean shutdown so music thread stops
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # handy shortcuts
        self.root.bind("<Control-Shift-C>", lambda e: self.open_contracts())
        self.root.bind("<Control-m>", lambda e: self.toggle_sound())
        self.root.bind("<Control-M>", lambda e: self.toggle_sound())

        # Reflect initial sound state on the button
        try:
            self.actions.set_sound_state(self.sound_enabled)
        except Exception:
            pass

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

        # Daily Double panel under Journal
        self.dd_panel = DailyDoublePanel(left)
        self.dd_panel.pack(side="top", fill="x", padx=4, pady=(0, 8))

        # Right column
        right = tk.Frame(grid, bg=COLORS["BG"])
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        self.logs = LogsPanel(right)
        self.logs.pack(fill="both", expand=True, padx=4, pady=0)

        # Bottom actions (Theme + Contracts + Sound toggle)
        try:
            self.actions = ActionsBar(
                self.root,
                on_atone=self.open_atone_dialog,
                on_sin=self.open_sin_dialog,
                on_theme=self.open_theme_picker,
                on_contracts=self.open_contracts,   # if supported
                on_faq=None,
                on_sound_toggle=self.toggle_sound,
            )
        except TypeError:
            # fallback for older ActionsBar signature (no sound toggle)
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
        # Theme-aware neutral trough color
        style.configure("Stat.Horizontal.TProgressbar",
                        troughcolor=COLORS.get("TRACK", "#D4D4D8"),
                        background=COLORS["ACCENT"])

    # ---------- Internal helpers ----------
    def _ensure_offers_today(self, min_count: int = 3):
        """Guarantee daily offers exist; resets stale flag if needed."""
        try:
            if generate_daily_contracts_if_needed:
                generate_daily_contracts_if_needed()
            if get_available_offers_count() < min_count:
                set_meta("offers_day", "")
                if generate_daily_contracts_if_needed:
                    generate_daily_contracts_if_needed()
        except Exception:
            # Don't block UI if anything goes wrong here
            pass

    # ---------- Refresh ----------
    def refresh_all(self, first=False):
        # Date + today lock
        is_today = (self.current_date == date.today())
        self.topbar.set_date(self.current_date, is_today)

        # Ensure there are time-limited offers today
        if is_today:
            self._ensure_offers_today()

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

        # Update Contracts button badge with # of available offers
        try:
            self.actions.set_contracts_badge(get_available_offers_count())
        except Exception:
            pass

        # Update sound button state (in case it changed elsewhere)
        try:
            self.actions.set_sound_state(self.sound_enabled)
        except Exception:
            pass

    # ---------- Sound toggle ----------
    def toggle_sound(self):
        self.sound_enabled = not self.sound_enabled
        muted = (not self.sound_enabled)
        # Persist + apply to SFX
        set_meta("sound_muted", "1" if muted else "0")
        try:
            set_muted(muted)
        except Exception:
            pass

        # Control BGM
        try:
            if muted:
                stop_bgm()
            else:
                start_bgm_shuffle(volume=0.22, crossfade_ms=700)
        except Exception:
            pass

        # Reflect in UI
        try:
            self.actions.set_sound_state(self.sound_enabled)
        except Exception:
            pass

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
        try:
            flash_widget(self.journal.status_label, times=2, on="#C7F9CC")
        except Exception:
            pass

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
                try: play_sfx("statsUp")
                except Exception: pass
            elif new_val < old_val:
                try: play_sfx("statsDown")
                except Exception: pass

        # XP + level-up SFX
        before = level_from_xp(get_total_xp())
        after_total = add_total_xp(pts * 10)
        after = level_from_xp(after_total)
        self.refresh_all()
        if after > before:
            try: play_sfx("levelUp")
            except Exception: pass
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
        win.title("Contracts")
        win.configure(bg=COLORS["BG"])
        win.geometry("720x520")
        win.grab_set()

        nb = ttk.Notebook(win)
        nb.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------- My Contracts tab ----------
        tab_my = tk.Frame(nb, bg=COLORS["BG"]); nb.add(tab_my, text="My Contracts")

        header = tk.Frame(tab_my, bg=COLORS["BG"]); header.pack(fill="x", padx=8, pady=(8, 2))
        tk.Label(header, text="Active Contracts", font=FONTS["h2"],
                 bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(side="left")

        list_my = tk.Frame(tab_my, bg=COLORS["BG"]); list_my.pack(fill="both", expand=True, padx=8, pady=6)

        # Personal creation area (with limits)
        form = tk.Frame(tab_my, bg=COLORS["CARD"]); form.pack(fill="x", padx=8, pady=(0, 10))
        tk.Label(form, text="Create personal contract (1–7 days)", font=FONTS["h3"],
                 bg=COLORS["CARD"], fg=COLORS["TEXT"]).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 2))
        title_var = tk.StringVar()
        tk.Entry(form, textvariable=title_var, width=40).grid(row=1, column=0, padx=(12,8), pady=8, sticky="w")
        days_var = tk.IntVar(value=3)
        tk.Label(form, text="Days:", bg=COLORS["CARD"], fg=COLORS["TEXT"]).grid(row=1, column=1, sticky="e")
        tk.Spinbox(form, from_=1, to=7, width=5, textvariable=days_var).grid(row=1, column=2, padx=(6,12), sticky="w")

        def create_personal():
            try:
                create_personal_contract_limited(title_var.get().strip(), int(days_var.get()))
            except ValueError as e:
                messagebox.showwarning("Cannot create", str(e), parent=win); return
            title_var.set("")
            refresh_views()

        RoundButton(form, "Create",
                    fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                    fg=COLORS["WHITE"], padx=14, pady=8, radius=12, command=create_personal)\
            .grid(row=1, column=3, padx=12, pady=8)

        # ---------- Available tab ----------
        tab_av = tk.Frame(nb, bg=COLORS["BG"]); nb.add(tab_av, text="Available Today")

        tk.Label(tab_av, text="Time-limited offers (claim before they expire)",
                 font=FONTS["h2"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(anchor="w", padx=8, pady=(8, 2))

        list_av = tk.Frame(tab_av, bg=COLORS["BG"]); list_av.pack(fill="both", expand=True, padx=8, pady=6)

        # ---------- helpers to render cards ----------
        def clear_children(parent):
            for w in parent.winfo_children():
                w.destroy()

        def card(parent, title, subtitle, right_btn=None):
            c = tk.Frame(parent, bg=COLORS["CARD"], bd=0, highlightthickness=0)
            c.pack(fill="x", pady=6)
            left = tk.Frame(c, bg=COLORS["CARD"]); left.pack(side="left", fill="both", expand=True)
            tk.Label(left, text=title, font=FONTS["h3"], bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=12, pady=(10,0))
            tk.Label(left, text=subtitle, font=FONTS["small"], bg=COLORS["CARD"], fg=COLORS["MUTED"]).pack(anchor="w", padx=12, pady=(0,10))
            if right_btn:
                box = tk.Frame(c, bg=COLORS["CARD"]); box.pack(side="right", padx=12)
                right_btn(box)
            return c

        def refresh_my():
            clear_children(list_my)
            # If your DB exposes get_active_contracts, use it; otherwise show a friendly message.
            try:
                from database import get_active_contracts  # runtime import to avoid ImportError at import time
                active = get_active_contracts(date.today().isoformat())
            except Exception:
                active = []
            if not active:
                tk.Label(list_my, text="No active contracts.", bg=COLORS["BG"], fg=COLORS["MUTED"]).pack(pady=8)
                return

            for cdata in active:
                title = cdata["title"]
                until = cdata.get("end_date")
                status = "BROKEN" if cdata.get("broken") else "ACTIVE"
                subtitle = f"Until {until}  •  Status: {status}  •  Penalty {cdata.get('penalty_xp',100)} XP"

                def make_btns(box, cid=cdata["id"]):
                    def break_it():
                        # Re-fetch current active list to avoid stale flags
                        try:
                            from database import get_active_contracts as _gac
                            _active = _gac(date.today().isoformat())
                        except Exception:
                            _active = []
                        target = next((c for c in _active if c["id"] == cid), None)

                        if not target:
                            messagebox.showinfo("Contract", "This contract is already inactive or broken.", parent=win)
                            refresh_views()
                            return

                        pen = int(target.get("penalty_xp", 100))
                        already = int(target.get("penalty_applied", 0)) == 1

                        # Mark broken
                        mark_contract_broken(cid)

                        if not already:
                            # Deduct once; same scale as elsewhere (pts*10)
                            add_total_xp(-abs(pen) * 10)
                            mark_contract_penalty_applied(cid)
                            try: play_sfx("statsDown")
                            except Exception: pass

                        messagebox.showinfo(
                            "Contract",
                            ("Penalty applied: -" + str(abs(pen)) + " XP." if not already else "Penalty already applied earlier."),
                            parent=win
                        )

                        refresh_views()
                        self.refresh_all()

                    RoundButton(box, "Mark Broken",
                                fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
                                fg=COLORS["WHITE"], padx=14, pady=8, radius=12, command=break_it).pack(pady=10)

                card(list_my, title, subtitle, right_btn=make_btns)

        def refresh_av():
            clear_children(list_av)
            offers = get_available_contracts()
            full = get_active_contracts_count() >= 3
            if not offers:
                tk.Label(list_av, text="No offers right now. Check again tomorrow!",
                         bg=COLORS["BG"], fg=COLORS["MUTED"]).pack(pady=8)
                return

            for o in offers:
                subtitle = f"Expires: {o['expires_at']}  •  Lasts: {o['duration_days']} day(s)  •  Penalty {o['penalty_xp']} XP"

                def make_btns(box, oid=o["id"]):
                    def claim():
                        try:
                            claim_contract_offer(oid)
                        except ValueError as e:
                            messagebox.showwarning("Cannot claim", str(e), parent=win); return
                        refresh_views(); self.refresh_all()

                    RoundButton(
                        box,
                        ("Full (3/3)" if full else "Claim"),
                        fill=(COLORS["MUTED"] if full else COLORS["PRIMARY"]),
                        hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                        fg=COLORS["WHITE"],
                        padx=14, pady=8, radius=12,
                        command=(None if full else claim),
                    ).pack(pady=10)

                card(list_av, o["title"], subtitle, right_btn=make_btns)

        def refresh_views():
            # disable personal creator if limits reached
            try:
                if get_personal_active_count() >= 1 or get_active_contracts_count() >= 3:
                    for child in form.winfo_children():
                        child.configure(state="disabled")
                else:
                    for child in form.winfo_children():
                        child.configure(state="normal")
            except Exception:
                pass
            refresh_my(); refresh_av()

        refresh_views()

    # ---------- Cleanup ----------
    def _on_close(self):
        try:
            stop_bgm()
        finally:
            self.root.destroy()
