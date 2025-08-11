# quiz.py — modal baseline quiz (old style, sliders 35–85)
import tkinter as tk
from tkinter import messagebox
from constants import POSITIVE_TRAITS, COLORS
from database import upsert_attribute, set_meta
from exp_system import set_total_xp

class BaselineQuiz(tk.Toplevel):
    def __init__(self, master, on_complete=None):
        super().__init__(master)
        self.title("Baseline Quiz — Set your starting attributes")
        self.geometry("620x640")
        self.configure(bg=COLORS["BG"])
        self.resizable(False, False)
        self.on_complete = on_complete
        self._build()

    def _build(self):
        tk.Label(self, text="Baseline Quiz", font=("Helvetica", 20, "bold"),
                 bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=10)
        tk.Label(self, text="Set a realistic baseline for each attribute (35–85).",
                 font=("Helvetica", 12), bg=COLORS["BG"], fg=COLORS["TEXT"]).pack()

        container = tk.Frame(self, bg=COLORS["BG"])
        container.pack(pady=10, fill="both", expand=True)

        self.vars = {}
        self.value_labels = {}
        for trait in POSITIVE_TRAITS:
            row = tk.Frame(container, bg=COLORS["BG"])
            row.pack(fill="x", padx=24, pady=10)

            tk.Label(row, text=trait, font=("Helvetica", 12, "bold"),
                     bg=COLORS["BG"], fg=COLORS["TEXT"], width=12, anchor="w").pack(side="left")

            var = tk.IntVar(value=50)
            s = tk.Scale(row, from_=35, to=85, orient="horizontal", variable=var,
                         bg=COLORS["BG"], fg=COLORS["TEXT"], troughcolor=COLORS["CARD"], length=360,
                         highlightthickness=0, relief="flat")
            s.pack(side="left", padx=8)
            self.vars[trait] = var

            val_lbl = tk.Label(row, text="50", font=("Helvetica", 12, "bold"),
                               bg=COLORS["BG"], fg=COLORS["TEXT"], width=3)
            val_lbl.pack(side="left")
            self.value_labels[trait] = val_lbl
            s.config(command=lambda v, lbl=val_lbl: lbl.config(text=str(int(float(v)))))

        tk.Button(self, text="Save baseline", command=self._save,
                  bg=COLORS["PRIMARY"], fg=COLORS["WHITE"], padx=16, pady=10).pack(pady=12)

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
