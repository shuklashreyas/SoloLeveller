import tkinter as tk
from constants import COLORS, FONTS
from widgets import RoundButton

class TopBar(tk.Frame):
    def __init__(self, master, on_prev, on_next):
        super().__init__(master, bg=COLORS["BG"])
        self.prev_btn = RoundButton(self, "←", command=on_prev,
                                    fill=COLORS["CARD"], hover_fill="#E3D4FF",
                                    fg=COLORS["TEXT"], padx=10, pady=6, radius=10)
        self.prev_btn.pack(side="left", padx=6)

        self.date_label = tk.Label(self, text="", font=FONTS["h2"],
                                   bg=COLORS["BG"], fg=COLORS["TEXT"])
        self.date_label.pack(side="left", expand=True)

        self.next_btn = RoundButton(self, "→", command=on_next,
                                    fill=COLORS["CARD"], hover_fill="#E3D4FF",
                                    fg=COLORS["TEXT"], padx=10, pady=6, radius=10)
        self.next_btn.pack(side="left", padx=6)

        self.rank_label = tk.Label(self, text="", font=FONTS["h3"],
                                   bg=COLORS["PRIMARY"], fg=COLORS["WHITE"], padx=12, pady=6)
        self.rank_label.pack(side="right", padx=8)

    def set_date(self, dt, is_today: bool):
        self.date_label.config(
            text=dt.strftime("%a, %b %d, %Y") + (" (today)" if is_today else "")
        )

    def set_rank(self, text: str):
        self.rank_label.config(text=text)
