# ui/components/dailydouble.py
import tkinter as tk
from constants import COLORS, FONTS

class DailyDoublePanel(tk.Frame):
    """Shows today's Daily Double picks (atone/sin) and their 2× effect."""
    def __init__(self, master):
        super().__init__(master, bg=COLORS["CARD"], bd=0, highlightthickness=0)
        tk.Label(self, text="Daily Double", font=FONTS["h3"], bg=COLORS["CARD"], fg=COLORS["TEXT"])\
            .pack(anchor="w", padx=12, pady=(10, 2))

        row = tk.Frame(self, bg=COLORS["CARD"]); row.pack(fill="x", padx=12, pady=(0, 10))
        self.lbl_atone = tk.Label(row, text="Atone: —", bg=COLORS["CARD"], fg=COLORS["GOOD"], font=FONTS["body"])
        self.lbl_atone.pack(side="left")
        self.lbl_sin = tk.Label(row, text="Sin: —", bg=COLORS["CARD"], fg=COLORS["BAD"], font=FONTS["body"])
        self.lbl_sin.pack(side="left", padx=16)

        tip = "Doing the Atone gives 2× XP; Sins in that category lose 2× XP."
        self.tip = tk.Label(self, text=tip, bg=COLORS["CARD"], fg=COLORS["MUTED"], font=FONTS["small"])
        self.tip.pack(anchor="w", padx=12)

    def set_values(self, atone_name: str, sin_name: str):
        self.lbl_atone.config(text=f"Atone: {atone_name}")
        self.lbl_sin.config(text=f"Sin: {sin_name}")
