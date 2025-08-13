# quiz.py — modal baseline quiz with descriptions + nicer fonts
import tkinter as tk
from tkinter import messagebox
from constants import POSITIVE_TRAITS, COLORS, FONTS, ATTR_DESCRIPTIONS
from database import upsert_attribute, set_meta
from exp_system import set_total_xp
from widgets import RoundButton

class BaselineQuiz(tk.Toplevel):
    def __init__(self, master, on_complete=None):
        super().__init__(master)
        self.title("Baseline Quiz — Set your starting attributes")
        self.geometry("720x720")
        self.configure(bg=COLORS["BG"])
        self.resizable(False, False)
        self.on_complete = on_complete
        self._build()

    def _build(self):
        tk.Label(self, text="Baseline Quiz", font=FONTS["h1"],
                 bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(14, 4))
        tk.Label(self, text="Set a realistic baseline for each attribute (35–85).",
                 font=FONTS["body"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack()

        container = tk.Frame(self, bg=COLORS["BG"])
        container.pack(pady=10, fill="both", expand=True)

        self.vars = {}
        for trait in POSITIVE_TRAITS:
            row = tk.Frame(container, bg=COLORS["BG"])
            row.pack(fill="x", padx=28, pady=8)

            left = tk.Frame(row, bg=COLORS["BG"])
            left.pack(side="left", fill="x", expand=True)
            right = tk.Frame(row, bg=COLORS["BG"])
            right.pack(side="left")

            tk.Label(left, text=trait, font=FONTS["h3"],
                     bg=COLORS["BG"], fg=COLORS["TEXT"], width=12, anchor="w").pack(anchor="w")

            v = tk.IntVar(value=50)
            s = tk.Scale(left, from_=35, to=85, orient="horizontal", variable=v,
                         bg=COLORS["BG"], fg=COLORS["TEXT"], troughcolor=COLORS["CARD"], length=460,
                         highlightthickness=0, relief="flat", showvalue=False)
            s.pack(anchor="w", pady=(2, 2))
            self.vars[trait] = v

            tk.Label(right, text="50", font=FONTS["h3"],
                     bg=COLORS["BG"], fg=COLORS["TEXT"], width=3).pack()
            s.config(command=lambda val, tr=trait, r=right: r.winfo_children()[0].config(text=str(int(float(val)))))

            # description under slider
            tk.Label(left, text=ATTR_DESCRIPTIONS[trait],
                     font=FONTS["small"], fg=COLORS["MUTED"], bg=COLORS["BG"]).pack(anchor="w", pady=(0, 4))

            btn = RoundButton(
        self, "Save baseline",
        command=self._save,
        fill=COLORS["PRIMARY"],          # was bg=
        hover_fill="#7A71FF",            # optional hover color
        fg=COLORS["WHITE"],
        padx=18, pady=10, radius=12      # radius if your RoundButton supports it
)

        btn.pack(pady=12)

        # modal
        self.grab_set()
        self.transient(self.master)

    def _save(self):
        for trait, var in self.vars.items():
            val = max(35, min(85, int(var.get())))
            upsert_attribute(trait, baseline=val, score=val)
        set_meta("quiz_done", "1")
        set_total_xp(0)
        messagebox.showinfo("Saved", "Baseline set! Let's get to work.", parent=self)
        if self.on_complete:
            self.on_complete()
        self.destroy()
