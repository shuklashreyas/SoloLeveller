import tkinter as tk
from constants import COLORS, FONTS
from widgets import RoundButton

class ActionsBar(tk.Frame):
    def __init__(self, master, on_atone, on_sin):
        super().__init__(master, bg=COLORS["BG"])
        self.atone_btn = RoundButton(self, "Atone",
                                     fill=COLORS["PRIMARY"], hover_fill="#7A71FF",
                                     fg=COLORS["WHITE"], padx=18, pady=10, radius=16,
                                     command=on_atone)
        self.atone_btn.pack(side="left", padx=12)
        self.sin_btn = RoundButton(self, "Sin",
                                   fill=COLORS["ACCENT"], hover_fill="#19B8C7",
                                   fg=COLORS["WHITE"], padx=18, pady=10, radius=16,
                                   command=on_sin)
        self.sin_btn.pack(side="left", padx=12)

        tk.Label(self, text="You can log only for TODAY.", font=FONTS["small"],
                 bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(side="right", padx=16)

    def enable(self, is_today: bool):
        self.atone_btn.enable(is_today)
        self.sin_btn.enable(is_today)
