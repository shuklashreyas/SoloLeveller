# ui.py — Gamey UI with rounded buttons, animations, and bigger journal font
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
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

        # First-run quiz (block until done)
        if get_meta("quiz_done") != "1":
            q = BaselineQuiz(self.root)
            self.root.wait_window(q)

        self.current_date = date.today()
        self.prev_stat_values = {t: STAT_MIN for t in POSITIVE_TRAITS}
        self.prev_xp_in_level = 0

        self._build_ui()
        self.refresh_all(first=True)

    # ---------- UI ----------
    def _build_ui(self):
        # Top bar
        top = tk.Frame(self.root, bg=COLORS["BG"])
        top.pack(fill="x", pady=(12, 6))

        self.prev_btn = RoundButton(top, "←", command=self.go_prev_day,
                                    fill=COLORS["CARD"], hover_fill="#E3D4FF",
                                    fg=COLORS["TEXT"], padx=10, pady=6, radius=10)
        self.prev_btn.pack(side="left", padx=6)

        self.date_label = tk.Label(top, text="", font=FONTS["h2"],
                                   bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.date_label.pack(side="left", expand=True)

        self.next_btn = RoundButton(top, "→", command=self.go_next_day,
                                    fill=COLORS["CARD"], hover_fill="#E3D4FF",
                                    fg=COLORS["TEXT"], padx=10, pady=6, radius=10)
        self.next_btn.pack(side="left", padx=6)

        self.rank_label = tk.Label(top, text="", font=FONTS["h3"],
                                   bg=COLORS["PRIMARY"], fg=COLORS["WHITE"], padx=12, pady=6)
        self.rank_label.pack(side="right", padx=8)

        # XP strip
        xp_strip = tk.Frame(self.root, bg=COLORS["BG"])
        xp_strip.pack(fill="x", pady=(0, 10))

        self.level_label = tk.Label(xp_strip, text="LVL 1", font=("Helvetica", 13, "bold"),
                                    bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.level_label.pack(side="left", padx=12)

        self.xp_var = tk.IntVar(value=0)
        self.xp_bar = ttk.Progressbar(xp_strip, orient="horizontal",
                                      mode="determinate", variable=self.xp_var, maximum=100,
                                      style="XP.Horizontal.TProgressbar", length=640)
        self.xp_bar.pack(side="left", padx=8, fill="x", expand=True)

        self.xp_text = tk.Label(xp_strip, text="0/100 XP", font=("Helvetica", 11),
                                bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.xp_text.pack(side="left", padx=8)

        # Main grid
        grid = tk.Frame(self.root, bg=COLORS["BG"])
        grid.pack(fill="both", expand=True, padx=12, pady=8)

        # Left column: Attributes + Journal
        left = tk.Frame(grid, bg=COLORS["BG"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        stats_card = tk.Frame(left, bg=COLORS["CARD"], bd=0, highlightthickness=0)
        stats_card.pack(side="top", fill="x", padx=4, pady=(0, 8))

        tk.Label(stats_card, text="Your Attributes", font=FONTS["h2"],
                 bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=16, pady=12)

        self.stat_rows = {}
        for trait in POSITIVE_TRAITS:
            row = tk.Frame(stats_card, bg=COLORS["CARD"])
            row.pack(fill="x", padx=16, pady=6)
            tk.Label(row, text=trait, font=FONTS["body"],
                     bg=COLORS["CARD"], fg=COLORS["TEXT"], width=12, anchor="w").pack(side="left")

            bar_var = tk.IntVar(value=STAT_MIN)
            ttk.Progressbar(row, orient="horizontal", length=320, mode="determinate",
                            maximum=STAT_MAX, variable=bar_var, style="Stat.Horizontal.TProgressbar")\
                .pack(side="left", padx=8, fill="x", expand=True)

            val_lbl = tk.Label(row, text=str(STAT_MIN), font=FONTS["body"],
                               bg=COLORS["CARD"], fg=COLORS["PRIMARY"], width=4)
            val_lbl.pack(side="left", padx=6)
            self.stat_rows[trait] = (bar_var, val_lbl)

        # Journal
        journal_card = tk.Frame(left, bg=COLORS["CARD"], bd=0, highlightthickness=0)
        journal_card.pack(side="top", fill="both", expand=True, padx=4, pady=(0, 4))
        tk.Label(journal_card, text="Journal", font=FONTS["h2"],
                 bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=16, pady=(12, 4))

        self.journal_text = tk.Text(journal_card, height=10, wrap="word",
                                    bg=COLORS["WHITE"], fg=COLORS["TEXT"],
                                    highlightthickness=0, relief="flat", font=("Helvetica", 13))
        self.journal_text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        j_actions = tk.Frame(journal_card, bg=COLORS["CARD"])
        j_actions.pack(fill="x", padx=12, pady=(0, 12))
        self.journal_status = tk.Label(j_actions, text="", bg=COLORS["CARD"], fg=COLORS["TEXT"], font=FONTS["small"])
        self.journal_status.pack(side="left")
        self.journal_save = RoundButton(j_actions, "Save Journal",
                                        fill=COLORS["PRIMARY"], hover_fill="#7A71FF",
                                        fg=COLORS["WHITE"], padx=16, pady=8, radius=12,
                                        command=self.save_journal)
        self.journal_save.pack(side="right")

        # Right column: Logs
        right = tk.Frame(grid, bg=COLORS["BG"])
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        logs_card = tk.Frame(right, bg=COLORS["CARD"], bd=0, highlightthickness=0)
        logs_card.pack(fill="both", expand=True, padx=4, pady=0)

        tk.Label(logs_card, text="Today’s Log", font=FONTS["h2"],
                 bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=16, pady=(12, 4))

        lists_frame = tk.Frame(logs_card, bg=COLORS["CARD"])
        lists_frame.pack(fill="both", expand=True, padx=12, pady=8)

        # Atoned
        atone_frame = tk.Frame(lists_frame, bg=COLORS["CARD"])
        atone_frame.pack(side="top", fill="both", expand=True, pady=(0, 8))
        tk.Label(atone_frame, text="Atoned", font=FONTS["h3"],
                 bg=COLORS["CARD"], fg=COLORS["PRIMARY"]).pack(anchor="w")
        self.atone_tree = ttk.Treeview(atone_frame, columns=("time", "desc", "points"),
                                       show="headings", height=7)
        for col, text in (("time", "Time"), ("desc", "What"), ("points", "+XP")):
            self.atone_tree.heading(col, text=text, anchor="center")
        self.atone_tree.column("time", width=110, anchor="center")
        self.atone_tree.column("desc", width=360, anchor="w")
        self.atone_tree.column("points", width=60, anchor="e")
        self.atone_tree.pack(fill="both", expand=True, pady=4)

        # Sinned
        sin_frame = tk.Frame(lists_frame, bg=COLORS["CARD"])
        sin_frame.pack(side="top", fill="both", expand=True, pady=(8, 0))
        tk.Label(sin_frame, text="Sinned", font=FONTS["h3"],
                 bg=COLORS["CARD"], fg=COLORS["ACCENT"]).pack(anchor="w")
        self.sin_tree = ttk.Treeview(sin_frame, columns=("time", "desc", "points"),
                                     show="headings", height=7)
        for col, text in (("time", "Time"), ("desc", "What"), ("points", "−XP")):
            self.sin_tree.heading(col, text=text, anchor="center")
        self.sin_tree.column("time", width=110, anchor="center")
        self.sin_tree.column("desc", width=360, anchor="w")
        self.sin_tree.column("points", width=60, anchor="e")
        self.sin_tree.pack(fill="both", expand=True, pady=4)

        # Striping
        for tree in (self.atone_tree, self.sin_tree):
            tree.tag_configure("odd", background="#FFFFFF")
            tree.tag_configure("even", background="#F8FAFC")

        # Bottom actions
        actions = tk.Frame(self.root, bg=COLORS["BG"])
        actions.pack(fill="x", pady=10)

        self.atone_btn = RoundButton(actions, "Atone",
                                     fill=COLORS["PRIMARY"], hover_fill="#7A71FF",
                                     fg=COLORS["WHITE"], padx=18, pady=10, radius=16,
                                     command=self.open_atone_dialog)
        self.atone_btn.pack(side="left", padx=12)

        self.sin_btn = RoundButton(actions, "Sin",
                                   fill=COLORS["ACCENT"], hover_fill="#19B8C7",
                                   fg=COLORS["WHITE"], padx=18, pady=10, radius=16,
                                   command=self.open_sin_dialog)
        self.sin_btn.pack(side="left", padx=12)

        self.today_only_note = tk.Label(actions, text="You can log only for TODAY.",
                                        font=FONTS["small"],
                                        bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.today_only_note.pack(side="right", padx=16)

    # ---------- Refresh ----------
    def refresh_all(self, first=False):
        # Date
        today = date.today()
        self.date_label.config(
            text=self.current_date.strftime("%a, %b %d, %Y") + (" (today)" if self.current_date == today else "")
        )

        # Stats
        stats = get_attributes()
        for trait, (bar_var, val_lbl) in self.stat_rows.items():
            new_val = stats.get(trait, {}).get("score", STAT_MIN)
            old_val = self.prev_stat_values.get(trait, STAT_MIN)
            animate_intvar(bar_var, old_val, new_val, duration_ms=350)
            val_lbl.config(text=str(new_val))
            self.prev_stat_values[trait] = new_val

        avg = average_stat({t: stats.get(t, {}).get("score", STAT_MIN) for t in POSITIVE_TRAITS})
        self.rank_label.config(text=f"Rank: {compute_rank(avg)}  •  Avg {avg}")

        # Entries
        for tree in (self.atone_tree, self.sin_tree):
            for iid in tree.get_children(): tree.delete(iid)
        for i, rec in enumerate(get_entries_by_date(self.current_date.isoformat())):
            when = rec["ts"][11:16]
            desc = f"[{rec['category']}] {rec['item']}"
            pts = rec["points"]
            tag = "odd" if (i % 2 == 0) else "even"
            if rec["entry_type"] == "ATONE":
                self.atone_tree.insert("", "end", values=(when, desc, f"+{pts}"), tags=(tag,))
            else:
                self.sin_tree.insert("", "end", values=(when, desc, str(pts)), tags=(tag,))

        # Today lock state
        is_today = (self.current_date == date.today())
        self.atone_btn.enable(is_today)
        self.sin_btn.enable(is_today)

        # Journal content + lock
        self.journal_text.config(state="normal")
        self.journal_text.delete("1.0", "end")
        self.journal_text.insert("1.0", get_journal(self.current_date.isoformat()))
        if is_today:
            self.journal_save.enable(True); self.journal_status.config(text="")
        else:
            self.journal_text.config(state="disabled")
            self.journal_save.enable(False)
            self.journal_status.config(text="(view-only for past/future dates)")

        # XP
        total = get_total_xp()
        lvl = level_from_xp(total)
        in_lvl = xp_in_level(total, lvl)
        need = xp_to_next(lvl)
        self.level_label.config(text=f"LVL {lvl}")
        self.xp_bar.configure(maximum=need)
        animate_intvar(self.xp_var, self.prev_xp_in_level if not first else 0, in_lvl, duration_ms=450)
        self.prev_xp_in_level = in_lvl
        self.xp_text.config(text=f"{in_lvl}/{need} XP")

    # ---------- Nav ----------
    def go_prev_day(self):
        self.current_date -= timedelta(days=1)
        self.refresh_all()

    def go_next_day(self):
        self.current_date += timedelta(days=1)
        self.refresh_all()

    # ---------- Journal ----------
    def save_journal(self):
        if self.current_date != date.today(): return
        upsert_journal(self.current_date.isoformat(), self.journal_text.get("1.0", "end").strip())
        self.journal_status.config(text="Saved.")
        flash_widget(self.journal_status, times=2, on="#C7F9CC")

    # ---------- Action dialogs ----------
    def open_atone_dialog(self):
        self._open_action_dialog("ATONE")

    def open_sin_dialog(self):
        self._open_action_dialog("SIN")

    def _open_action_dialog(self, kind: str):
        if self.current_date != date.today():
            messagebox.showinfo("Not allowed", "You can only log for today."); return

        dialog = tk.Toplevel(self.root)
        dialog.title("Atone" if kind == "ATONE" else "Sin")
        dialog.geometry("560x380")
        dialog.configure(bg=COLORS["BG"])
        dialog.grab_set()

        tk.Label(dialog, text=("Choose a positive attribute" if kind == "ATONE" else "Choose a sin"),
                 font=FONTS["h3"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(12, 6))

        if kind == "ATONE":
            categories, menu_map = POSITIVE_TRAITS, ATONE_MENU
        else:
            categories, menu_map = SINS, SIN_MENU

        cat_var = tk.StringVar(value=categories[0])
        cat_combo = ttk.Combobox(dialog, values=categories, textvariable=cat_var, state="readonly")
        cat_combo.pack(pady=4)

        tk.Label(dialog, text="Pick an item", bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(10, 2))
        act_var = tk.StringVar()
        act_combo = ttk.Combobox(dialog, values=[], textvariable=act_var, state="readonly", width=46)
        act_combo.pack(pady=4)

        other_text = tk.Text(dialog, height=3, width=52, bg=COLORS["CARD"], fg=COLORS["TEXT"],
                             highlightthickness=0, relief="flat", font=FONTS["body"])
        other_text.pack(pady=6); other_text.pack_forget()

        info_lbl = tk.Label(dialog, text="", bg=COLORS["BG"], fg=COLORS["TEXT"])
        info_lbl.pack()

        def load_items(*_):
            items = [name for (name, _) in menu_map.get(cat_var.get(), [])]
            act_combo.config(values=items)
            if items: act_combo.current(0); update_info()

        def update_info(*_):
            other_text.pack_forget()
            sel, pts = act_var.get(), 0
            for (name, p) in menu_map.get(cat_var.get(), []):
                if name == sel: pts = p; break
            if sel == "Other…":
                info_lbl.config(text=("Choose intensity (1–3). " + ("Gain XP." if kind=="ATONE" else "Lose XP.")))
                other_text.pack(pady=6)
            else:
                info_lbl.config(text=f"{'Default XP gain' if kind=='ATONE' else 'Default XP loss'}: {('+' if kind=='ATONE' else '')}{pts}")

        cat_combo.bind("<<ComboboxSelected>>", load_items)
        act_combo.bind("<<ComboboxSelected>>", update_info)
        load_items()

        def save():
            cat, act = cat_var.get(), act_var.get()
            if not cat or not act:
                messagebox.showwarning("Missing", "Please choose a category and an item.", parent=dialog); return

            pts = None
            for (name, p) in menu_map.get(cat, []):
                if name == act: pts = p; break

            if act == "Other…":
                custom = other_text.get("1.0", "end").strip()
                if not custom:
                    messagebox.showwarning("Missing", "Describe what you did.", parent=dialog); return
                intensity = simpledialog.askinteger("Intensity", "Pick 1 (light) to 3 (major).",
                                                    minvalue=1, maxvalue=3, parent=dialog)
                if intensity is None: return
                pts = intensity * (1 if kind == "ATONE" else -1)
                act_final = custom
            else:
                act_final = act
            if pts is None or pts == 0:
                pts = 2 if kind == "ATONE" else -2

            insert_entry(self.current_date.isoformat(), kind, cat, act_final, pts)

            if kind == "ATONE":
                update_attribute_score(cat, abs(pts))
            else:
                target = SIN_TO_ATTRIBUTE.get(cat)
                if target: update_attribute_score(target, pts)

            before = level_from_xp(get_total_xp())
            after_total = add_total_xp(pts * 10)
            after = level_from_xp(after_total)
            self.refresh_all()
            if after > before:
                messagebox.showinfo("LEVEL UP!", f"You reached Level {after}!", parent=dialog)

            dialog.destroy()

        RoundButton(dialog, "Save",
                    fill=COLORS["PRIMARY"] if kind=="ATONE" else COLORS["ACCENT"],
                    hover_fill="#7A71FF" if kind=="ATONE" else "#19B8C7",
                    fg=COLORS["WHITE"], padx=14, pady=8, radius=12, command=save).pack(pady=12)

    def is_today(self):
        return self.current_date == date.today()
