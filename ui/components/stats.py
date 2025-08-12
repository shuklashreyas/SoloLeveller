import tkinter as tk
from tkinter import ttk
from constants import COLORS, FONTS, POSITIVE_TRAITS, STAT_MIN, STAT_MAX
from animations import animate_intvar

class StatsPanel(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=COLORS["CARD"], bd=0, highlightthickness=0)
        tk.Label(self, text="Your Attributes", font=FONTS["h2"],
                 bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=16, pady=12)
        self.rows = {}
        for trait in POSITIVE_TRAITS:
            row = tk.Frame(self, bg=COLORS["CARD"])
            row.pack(fill="x", padx=16, pady=6)
            tk.Label(row, text=trait, font=FONTS["body"],
                     bg=COLORS["CARD"], fg=COLORS["TEXT"], width=12, anchor="w").pack(side="left")
            var = tk.IntVar(value=STAT_MIN)
            ttk.Progressbar(row, orient="horizontal", length=320, mode="determinate",
                            maximum=STAT_MAX, variable=var, style="Stat.Horizontal.TProgressbar")\
                .pack(side="left", padx=8, fill="x", expand=True)
            val_lbl = tk.Label(row, text=str(STAT_MIN), font=FONTS["body"],
                               bg=COLORS["CARD"], fg=COLORS["PRIMARY"], width=4)
            val_lbl.pack(side="left", padx=6)
            self.rows[trait] = (var, val_lbl)

    def set_value(self, trait, old_val, new_val):
        var, lbl = self.rows[trait]
        animate_intvar(var, old_val, new_val, duration_ms=350)
        lbl.config(text=str(new_val))
