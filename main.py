
# Habit Tracker — Solo Level-Up Edition (Gamey v2)
# Tech: Python + Tkinter + SQLite
# Run: python main.py

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date, timedelta
from database import (
    initialize_db, get_meta, set_meta,
    get_attributes, upsert_attribute, update_attribute_score,
    insert_entry, get_entries_by_date
)

APP_TITLE = "Habit Tracker — Solo Level-Up"

# ---- Color Palette (from bite-club.hex) ----
COLORS = {
    "BG": "#74AEFF",
    "CARD": "#C355DA",
    "PRIMARY": "#050002",
    "ACCENT": "#171237",
    "TEXT": "#050002",
    "WHITE": "#FFFFFF"
}

# ---- Traits & Sins ----
POSITIVE_TRAITS = [
    "Spiritual", "Physical", "Mindful", "Social",
    "Integrity", "Intellect", "Character"
]

SINS = ["Pride", "Greed", "Lust", "Envy", "Gluttony", "Wrath", "Sloth"]

# Map each sin to which positive attribute it reduces.
SIN_TO_ATTRIBUTE = {
    "Pride": "Character",
    "Greed": "Spiritual",
    "Lust": "Integrity",
    "Envy": "Spiritual",
    "Gluttony": "Physical",
    "Wrath": "Social",
    "Sloth": "Mindful",
}

# Activity menus
ATONE_MENU = {
    "Spiritual": [
        ("Meditation (10m+)", 2),
        ("Journal or Gratitude", 2),
        ("Prayer / Reflection", 2),
        ("Nature walk", 2),
        ("Acts of service", 3),
        ("Read philosophy/spiritual", 2),
        ("Other…", 0),
    ],
    "Physical": [
        ("Workout / Lifting", 3),
        ("Play a sport", 3),
        ("Cardio (20m+)", 2),
        ("Walk 10k steps", 2),
        ("Stretch / Mobility", 1),
        ("Other…", 0),
    ],
    "Mindful": [
        ("Deep work 60+ min", 3),
        ("Pomodoro 25m", 1),
        ("No social media block", 3),
        ("Breathing practice", 1),
        ("Other…", 0),
    ],
    "Social": [
        ("Family time", 2),
        ("Friends / loved ones", 2),
        ("Made a new connection", 2),
        ("Called someone", 1),
        ("Other…", 0),
    ],
    "Integrity": [
        ("Completed plan/schedule", 3),
        ("Kept a promise", 2),
        ("Woke up on time", 2),
        ("Chore / Errand done", 1),
        ("Other…", 0),
    ],
    "Intellect": [
        ("Watched educational pod/vid", 2),
        ("Read 20+ pages", 2),
        ("Course / Lecture / Class", 3),
        ("Practice (coding/math etc.)", 2),
        ("Other…", 0),
    ],
    "Character": [
        ("Helped someone", 2),
        ("Random act of kindness", 2),
        ("Volunteered", 3),
        ("Apologized / Owned mistake", 2),
        ("Other…", 0),
    ],
}

SIN_MENU = {
    "Pride": [
        ("Bragging / belittling", -2),
        ("Dismissed feedback", -2),
        ("Other…", 0),
    ],
    "Greed": [
        ("Cut corners for gain", -3),
        ("Money-obsessed spiral", -2),
        ("Other…", 0),
    ],
    "Lust": [
        ("NSFW rabbit hole", -3),
        ("Sexual distraction from goals", -2),
        ("Other…", 0),
    ],
    "Envy": [
        ("Compared self on LinkedIn/IG", -2),
        ("Resentment towards peers", -2),
        ("Other…", 0),
    ],
    "Gluttony": [
        ("Binge eating/junk", -3),
        ("Sugary drinks excess", -2),
        ("Other…", 0),
    ],
    "Wrath": [
        ("Angry outburst", -3),
        ("Online arguments", -2),
        ("Other…", 0),
    ],
    "Sloth": [
        ("Skipped work/study", -3),
        ("Procrastinated session", -2),
        ("Slept way past plan", -2),
        ("Other…", 0),
    ],
}

STAT_MIN = 35
STAT_MAX = 99

RANKS = [
    (35, 44, "Novice"),
    (45, 54, "Apprentice"),
    (55, 64, "Challenger"),
    (65, 74, "Adept"),
    (75, 84, "Disciplined"),
    (85, 92, "Master"),
    (93, 99, "Transcendent"),
]

# ---- XP / Level System ----
# Simple progression: XP to next level grows linearly by +50 each level, starting at 100.
def xp_to_next(level: int) -> int:
    return 100 + (level - 1) * 50

def xp_threshold(level: int) -> int:
    # cumulative XP required to reach the start of 'level'
    # level 1 starts at 0
    if level <= 1:
        return 0
    total = 0
    for l in range(1, level):
        total += xp_to_next(l)
    return total

def level_from_xp(total_xp: int) -> int:
    level = 1
    while total_xp >= xp_threshold(level + 1):
        level += 1
    return level

def xp_in_level(total_xp: int, level: int) -> int:
    return total_xp - xp_threshold(level)

def get_total_xp() -> int:
    v = get_meta("xp")
    try:
        return int(v) if v is not None else 0
    except ValueError:
        return 0

def set_total_xp(xp: int):
    set_meta("xp", str(max(0, int(xp))))

def add_total_xp(delta: int) -> int:
    cur = get_total_xp()
    new = cur + int(delta)
    if new < 0: new = 0
    set_total_xp(new)
    return new

def average_stat(stats: dict) -> int:
    if not stats:
        return 0
    vals = [stats.get(trait, STAT_MIN) for trait in POSITIVE_TRAITS]
    return int(round(sum(vals) / len(vals)))

def compute_rank(avg: int) -> str:
    for lo, hi, name in RANKS:
        if lo <= avg <= hi:
            return name
    return "Unranked"

class HabitTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("980x740")
        self.root.configure(bg=COLORS["BG"])

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        # High-contrast ttk tweaks
        style.configure("TLabel", foreground=COLORS["TEXT"], background=COLORS["CARD"])
        style.configure("TButton", foreground=COLORS["TEXT"])
        style.configure("Treeview",
                        background=COLORS["CARD"],
                        fieldbackground=COLORS["CARD"],
                        foreground=COLORS["TEXT"])
        style.configure("Treeview.Heading",
                        background=COLORS["ACCENT"],
                        foreground=COLORS["TEXT"])

        initialize_db()

        if get_meta("quiz_done") != "1":
            self.run_baseline_quiz()

        self.current_date = date.today()

        self._build_ui()
        self.refresh_all()

    # ---------- UI ----------
    def _build_ui(self):
        # Top bar
        top = tk.Frame(self.root, bg=COLORS["BG"])
        top.pack(fill="x", pady=(12, 6))

        self.prev_btn = tk.Button(top, text="←", width=3, command=self.go_prev_day,
                                  bg=COLORS["CARD"], fg=COLORS["TEXT"],
                                  activebackground=COLORS["ACCENT"])
        self.prev_btn.pack(side="left", padx=8)

        self.date_label = tk.Label(top, text="", font=("Helvetica", 18, "bold"),
                                   bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.date_label.pack(side="left", expand=True)

        self.next_btn = tk.Button(top, text="→", width=3, command=self.go_next_day,
                                  bg=COLORS["CARD"], fg=COLORS["TEXT"],
                                  activebackground=COLORS["ACCENT"])
        self.next_btn.pack(side="left", padx=8)

        self.rank_label = tk.Label(top, text="", font=("Helvetica", 14, "bold"),
                                   bg=COLORS["PRIMARY"], fg=COLORS["WHITE"], padx=12, pady=6)
        self.rank_label.pack(side="right", padx=8)

        # XP strip
        xp_strip = tk.Frame(self.root, bg=COLORS["BG"])
        xp_strip.pack(fill="x", pady=(0, 10))

        self.level_label = tk.Label(xp_strip, text="LVL 1", font=("Helvetica", 13, "bold"),
                                    bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.level_label.pack(side="left", padx=12)

        self.xp_var = tk.IntVar(value=0)
        self.xp_bar = ttk.Progressbar(xp_strip, orient="horizontal", length=640,
                                      mode="determinate", variable=self.xp_var, maximum=100)
        self.xp_bar.pack(side="left", padx=8, fill="x", expand=True)

        self.xp_text = tk.Label(xp_strip, text="0/100 XP", font=("Helvetica", 11),
                                bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.xp_text.pack(side="left", padx=8)

        # Center layout
        center = tk.Frame(self.root, bg=COLORS["BG"])
        center.pack(fill="both", expand=True, padx=16, pady=8)

        # Stats card
        stats_card = tk.Frame(center, bg=COLORS["CARD"], bd=0, highlightthickness=0)
        stats_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(stats_card, text="Your Attributes", font=("Helvetica", 16, "bold"),
                 bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=16, pady=12)

        self.stat_rows = {}
        for trait in POSITIVE_TRAITS:
            row = tk.Frame(stats_card, bg=COLORS["CARD"])
            row.pack(fill="x", padx=16, pady=6)
            lbl = tk.Label(row, text=f"{trait}", font=("Helvetica", 12, "bold"),
                           bg=COLORS["CARD"], fg=COLORS["TEXT"], width=12, anchor="w")
            lbl.pack(side="left")

            bar_var = tk.IntVar(value=STAT_MIN)
            bar = ttk.Progressbar(row, orient="horizontal", length=320, mode="determinate",
                                  maximum=STAT_MAX, variable=bar_var)
            bar.pack(side="left", padx=8)

            val_lbl = tk.Label(row, text=f"{STAT_MIN}", font=("Helvetica", 12, "bold"),
                               bg=COLORS["CARD"], fg=COLORS["PRIMARY"], width=4)
            val_lbl.pack(side="left", padx=6)

            self.stat_rows[trait] = (bar_var, val_lbl)

        # Right: Today's entries
        right = tk.Frame(center, bg=COLORS["CARD"])
        right.pack(side="left", fill="both", expand=True, padx=(8, 0))

        tk.Label(right, text="Today’s Log", font=("Helvetica", 16, "bold"),
                 bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=16, pady=(12, 4))

        lists_frame = tk.Frame(right, bg=COLORS["CARD"])
        lists_frame.pack(fill="both", expand=True, padx=12, pady=8)

        # Atoned
        atone_frame = tk.Frame(lists_frame, bg=COLORS["CARD"])
        atone_frame.pack(side="top", fill="both", expand=True, pady=(0, 8))

        tk.Label(atone_frame, text="Atoned", font=("Helvetica", 13, "bold"),
                 bg=COLORS["CARD"], fg=COLORS["PRIMARY"]).pack(anchor="w")

        self.atone_tree = ttk.Treeview(atone_frame, columns=("time", "desc", "points"),
                                       show="headings", height=6)
        self.atone_tree.heading("time", text="Time")
        self.atone_tree.heading("desc", text="What")
        self.atone_tree.heading("points", text="+XP")
        self.atone_tree.column("time", width=110, anchor="center")
        self.atone_tree.column("desc", width=320, anchor="w")
        self.atone_tree.column("points", width=60, anchor="e")
        self.atone_tree.pack(fill="both", expand=True, pady=4)

        # Sinned
        sin_frame = tk.Frame(lists_frame, bg=COLORS["CARD"])
        sin_frame.pack(side="top", fill="both", expand=True, pady=(8, 0))

        tk.Label(sin_frame, text="Sinned", font=("Helvetica", 13, "bold"),
                 bg=COLORS["CARD"], fg=COLORS["ACCENT"]).pack(anchor="w")

        self.sin_tree = ttk.Treeview(sin_frame, columns=("time", "desc", "points"),
                                     show="headings", height=6)
        self.sin_tree.heading("time", text="Time")
        self.sin_tree.heading("desc", text="What")
        self.sin_tree.heading("points", text="−XP")
        self.sin_tree.column("time", width=110, anchor="center")
        self.sin_tree.column("desc", width=320, anchor="w")
        self.sin_tree.column("points", width=60, anchor="e")
        self.sin_tree.pack(fill="both", expand=True, pady=4)

        # Bottom actions
        actions = tk.Frame(self.root, bg=COLORS["BG"])
        actions.pack(fill="x", pady=10)

        self.atone_btn = tk.Button(actions, text="Atone", font=("Helvetica", 13, "bold"),
                                   bg=COLORS["PRIMARY"], fg=COLORS["WHITE"],
                                   activebackground=COLORS["ACCENT"], padx=18, pady=8,
                                   command=self.open_atone_dialog)
        self.atone_btn.pack(side="left", padx=12)

        self.sin_btn = tk.Button(actions, text="Sin", font=("Helvetica", 13, "bold"),
                                 bg=COLORS["ACCENT"], fg=COLORS["WHITE"],
                                 activebackground=COLORS["PRIMARY"], padx=18, pady=8,
                                 command=self.open_sin_dialog)
        self.sin_btn.pack(side="left", padx=12)

        self.today_only_note = tk.Label(actions, text="You can log only for TODAY.",
                                        font=("Helvetica", 10, "italic"),
                                        bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.today_only_note.pack(side="right", padx=16)

    # ---------- Quiz (modal Toplevel; no second root) ----------
    def run_baseline_quiz(self):
        quiz = tk.Toplevel(self.root)
        quiz.title("Baseline Quiz — Set your starting attributes")
        quiz.geometry("560x560")
        quiz.configure(bg=COLORS["BG"])
        quiz.grab_set()

        tk.Label(quiz, text="Baseline Quiz", font=("Helvetica", 18, "bold"),
                 bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=10)

        tk.Label(quiz, text="Set a realistic baseline for each attribute (35–85).",
                 font=("Helvetica", 11), bg=COLORS["BG"], fg=COLORS["TEXT"]).pack()

        container = tk.Frame(quiz, bg=COLORS["BG"])
        container.pack(pady=10, fill="both", expand=True)

        sliders = {}
        for trait in POSITIVE_TRAITS:
            row = tk.Frame(container, bg=COLORS["BG"])
            row.pack(fill="x", padx=16, pady=8)

            tk.Label(row, text=trait, font=("Helvetica", 12, "bold"),
                     bg=COLORS["BG"], fg=COLORS["TEXT"], width=12, anchor="w").pack(side="left")

            var = tk.IntVar(value=50)
            s = tk.Scale(row, from_=35, to=85, orient="horizontal", variable=var,
                         bg=COLORS["BG"], fg=COLORS["TEXT"], troughcolor=COLORS["CARD"], length=320,
                         highlightthickness=0)
            s.pack(side="left", padx=8)
            sliders[trait] = var

        def submit():
            for trait in POSITIVE_TRAITS:
                val = int(sliders[trait].get())
                val = max(35, min(85, val))
                upsert_attribute(trait, baseline=val, score=val)
            set_meta("quiz_done", "1")
            # reset XP on fresh start
            set_total_xp(0)
            messagebox.showinfo("Saved", "Baseline set! Let's get to work.", parent=quiz)
            quiz.destroy()

        tk.Button(quiz, text="Save baseline", command=submit,
                  bg=COLORS["PRIMARY"], fg=COLORS["WHITE"], padx=16, pady=8).pack(pady=12)

        self.root.wait_window(quiz)

    # ---------- Navigation ----------
    def go_prev_day(self):
        self.current_date -= timedelta(days=1)
        self.refresh_all()

    def go_next_day(self):
        self.current_date += timedelta(days=1)
        self.refresh_all()

    # ---------- Refresh helpers ----------
    def refresh_all(self):
        self._refresh_date_label()
        self._refresh_stats()
        self._refresh_entries()
        self._refresh_actions_state()
        self._refresh_xp_ui()

    def _refresh_date_label(self):
        today = date.today()
        label = self.current_date.strftime("%a, %b %d, %Y")
        suffix = " (today)" if self.current_date == today else ""
        self.date_label.config(text=label + suffix)

    def _refresh_stats(self):
        stats = get_attributes()
        for trait, (bar_var, val_lbl) in self.stat_rows.items():
            score = stats.get(trait, {}).get("score", STAT_MIN)
            bar_var.set(score)
            val_lbl.config(text=str(score))

        avg = average_stat({t: stats.get(t, {}).get("score", STAT_MIN) for t in POSITIVE_TRAITS})
        rank = compute_rank(avg)
        self.rank_label.config(text=f"Rank: {rank}  •  Avg {avg}")

    def _refresh_entries(self):
        for tree in (self.atone_tree, self.sin_tree):
            for iid in tree.get_children():
                tree.delete(iid)

        records = get_entries_by_date(self.current_date.isoformat())
        for rec in records:
            when = rec["ts"][11:16]
            desc = f"[{rec['category']}] {rec['item']}"
            pts = rec["points"]
            if rec["entry_type"] == "ATONE":
                self.atone_tree.insert("", "end", values=(when, desc, f"+{pts}"))
            else:
                self.sin_tree.insert("", "end", values=(when, desc, str(pts)))

    def _refresh_actions_state(self):
        is_today = (self.current_date == date.today())
        state = tk.NORMAL if is_today else tk.DISABLED
        self.atone_btn.config(state=state)
        self.sin_btn.config(state=state)

    def _refresh_xp_ui(self):
        total = get_total_xp()
        lvl = level_from_xp(total)
        in_lvl = xp_in_level(total, lvl)
        need = xp_to_next(lvl)
        self.level_label.config(text=f"LVL {lvl}")
        self.xp_bar.configure(maximum=need)
        self.xp_var.set(in_lvl)
        self.xp_text.config(text=f"{in_lvl}/{need} XP")

    # ---------- Dialogs ----------
    def open_atone_dialog(self):
        self._open_action_dialog(kind="ATONE")

    def open_sin_dialog(self):
        self._open_action_dialog(kind="SIN")

    def _open_action_dialog(self, kind="ATONE"):
        if self.current_date != date.today():
            messagebox.showinfo("Not allowed", "You can only log for today.")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Atone" if kind == "ATONE" else "Sin")
        dialog.geometry("520x360")
        dialog.configure(bg=COLORS["BG"])
        dialog.grab_set()

        tk.Label(dialog, text=("Choose a positive attribute" if kind == "ATONE" else "Choose a sin"),
                 font=("Helvetica", 13, "bold"), bg=COLORS["BG"],
                 fg=COLORS["TEXT"]).pack(pady=(12, 6))

        category_var = tk.StringVar()
        if kind == "ATONE":
            categories = POSITIVE_TRAITS
            menu_map = ATONE_MENU
        else:
            categories = SINS
            menu_map = SIN_MENU

        cat_combo = ttk.Combobox(dialog, values=categories, textvariable=category_var, state="readonly")
        cat_combo.pack(pady=4)
        cat_combo.current(0)

        tk.Label(dialog, text="Pick an item", bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(10, 2))
        activity_var = tk.StringVar()
        activity_combo = ttk.Combobox(dialog, values=[], textvariable=activity_var, state="readonly", width=42)
        activity_combo.pack(pady=4)

        other_text = tk.Text(dialog, height=3, width=48, bg=COLORS["CARD"], fg=COLORS["TEXT"])
        other_text.pack(pady=6)
        other_text.pack_forget()

        points_label = tk.Label(dialog, text="", bg=COLORS["BG"], fg=COLORS["TEXT"])
        points_label.pack()

        def on_category_change(event=None):
            cat = category_var.get()
            items = [name for (name, pts) in menu_map.get(cat, [])]
            activity_combo.config(values=items)
            if items:
                activity_combo.current(0)
                update_points_label()

        def update_points_label(event=None):
            cat = category_var.get()
            selection = activity_var.get()
            other_text.pack_forget()
            pts = 0
            for (name, p) in menu_map.get(cat, []):
                if name == selection:
                    pts = p
                    break
            if selection == "Other…":
                points_label.config(text=("Choose intensity (1–3). " + ("Gain XP." if kind=="ATONE" else "Lose XP.")))
                other_text.pack(pady=6)
            else:
                if kind == "ATONE":
                    points_label.config(text=f"Default XP gain: +{pts}  (Attributes +{pts})")
                else:
                    points_label.config(text=f"Default XP loss: {pts}  (Attributes {pts})")

        cat_combo.bind("<<ComboboxSelected>>", on_category_change)
        activity_combo.bind("<<ComboboxSelected>>", update_points_label)
        on_category_change()

        def save():
            cat = category_var.get()
            act = activity_var.get()
            if not cat or not act:
                messagebox.showwarning("Missing", "Please choose a category and an item.", parent=dialog)
                return

            pts = None
            for (name, p) in menu_map.get(cat, []):
                if name == act:
                    pts = p
                    break

            if act == "Other…":
                text = other_text.get("1.0", "end").strip()
                if not text:
                    messagebox.showwarning("Missing", "Describe what you did.", parent=dialog)
                    return
                intensity = simpledialog.askinteger(
                    "Intensity", "Pick an intensity from 1 (light) to 3 (major).", minvalue=1, maxvalue=3, parent=dialog
                )
                if intensity is None:
                    return
                pts = intensity * (1 if kind == "ATONE" else -1)
                act_final = text
            else:
                act_final = act

            if pts is None or pts == 0:
                pts = 2 if kind == "ATONE" else -2

            # Insert entry
            insert_entry(date=self.current_date.isoformat(),
                         entry_type=kind,
                         category=cat,
                         item=act_final,
                         points=pts)

            # Attribute change
            if kind == "ATONE":
                update_attribute_score(cat, delta=abs(pts))
            else:
                target = SIN_TO_ATTRIBUTE.get(cat)
                if target:
                    update_attribute_score(target, delta=pts)

            # XP change (scaled for game feel)
            # Each point ~ 10 XP.
            delta_xp = pts * 10  # pts is + for atone, - for sin
            before_level = level_from_xp(get_total_xp())
            total_after = add_total_xp(delta_xp)
            after_level = level_from_xp(total_after)

            self.refresh_all()
            if after_level > before_level:
                messagebox.showinfo("LEVEL UP!", f"You reached Level {after_level}!", parent=dialog)

            dialog.destroy()

        tk.Button(dialog, text="Save", command=save,
                  bg=COLORS["PRIMARY"] if kind=="ATONE" else COLORS["ACCENT"],
                  fg=COLORS["WHITE"], padx=14, pady=8).pack(pady=12)

    def is_today(self):
        return self.current_date == date.today()


if __name__ == "__main__":
    root = tk.Tk()
    app = HabitTrackerApp(root)
    root.mainloop()
