# ui/components/topbar.py
import tkinter as tk
from datetime import date
from constants import COLORS, FONTS
from widgets import RoundButton

class TopBar(tk.Frame):
    def __init__(self, master, on_prev, on_next, on_calendar=None):
        super().__init__(master, bg=COLORS["BG"])

        # Left cluster: prev ◀  [Date]  ▶ next
        left = tk.Frame(self, bg=COLORS["BG"])
        left.pack(side="left")

        self.prev_btn = RoundButton(
            left, "◀",
            fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["TEXT"], padx=10, pady=6, radius=12,
            command=on_prev
        )
        self.prev_btn.pack(side="left", padx=6)

        self._date_var = tk.StringVar(value="")
        self.date_label = tk.Label(
            left, textvariable=self._date_var,
            font=FONTS["h2"], bg=COLORS["BG"], fg=COLORS["TEXT"]
        )
        self.date_label.pack(side="left", padx=8)

        self.next_btn = RoundButton(
            left, "▶",
            fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["TEXT"], padx=10, pady=6, radius=12,
            command=on_next
        )
        self.next_btn.pack(side="left", padx=6)

        # Center cluster: currency (coins + shards)
        center = tk.Frame(self, bg=COLORS["BG"])
        center.pack(side="left", expand=True)

        # Currency display (coins + shards)
        self._coins_var = tk.StringVar(value="0")
        self._shards_var = tk.StringVar(value="0")
        # Try to load images with tkinter.PhotoImage (no PIL dependency)
        try:
            coin_img = None
            shard_img = None
            try:
                coin_img = tk.PhotoImage(file="images/coin.png")
                # subsample to reduce size if image is large
                try:
                    coin_img = coin_img.subsample(6, 6)
                except Exception:
                    pass
            except Exception:
                coin_img = None
            try:
                shard_img = tk.PhotoImage(file="images/shard.png")
                try:
                    shard_img = shard_img.subsample(6, 6)
                except Exception:
                    pass
            except Exception:
                shard_img = None
            self._coin_img = coin_img
            self._shard_img = shard_img
        except Exception:
            self._coin_img = None
            self._shard_img = None

        # Layout: coin icon + value, shard icon + value
        if self._coin_img:
            coin_icon = tk.Label(center, image=self._coin_img, bg=COLORS["BG"]) ; coin_icon.pack(side="left", padx=(4,2))
        coin_lbl = tk.Label(center, textvariable=self._coins_var, font=FONTS["small"], bg=COLORS["BG"], fg=COLORS["MUTED"]) ; coin_lbl.pack(side="left", padx=(2,8))
        if self._shard_img:
            shard_icon = tk.Label(center, image=self._shard_img, bg=COLORS["BG"]) ; shard_icon.pack(side="left", padx=(4,2))
        shard_lbl = tk.Label(center, textvariable=self._shards_var, font=FONTS["small"], bg=COLORS["BG"], fg=COLORS["MUTED"]) ; shard_lbl.pack(side="left", padx=(2,4))

        right = tk.Frame(self, bg=COLORS["BG"])
        right.pack(side="right")

        if on_calendar:
            self.cal_btn = RoundButton(
                right, "📅",  # change to "Cal" if you prefer no emoji
                fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS["TEXT"], padx=10, pady=6, radius=12,
                command=on_calendar
            )
            self.cal_btn.pack(side="right", padx=6)

        self._rank_var = tk.StringVar(value="")
        self.rank_label = tk.Label(
            right, textvariable=self._rank_var,
            font=FONTS["small"], bg=COLORS["BG"], fg=COLORS["MUTED"]
        )
        self.rank_label.pack(side="right", padx=8)

        # Spacer to keep things tidy
        tk.Label(self, text="", bg=COLORS["BG"]).pack(side="right", expand=True)

    # --- API used by app.py ---

    def set_date(self, d: date, is_today: bool):
        # Example: Fri 15 Aug 2025  (append "• Today" if you want)
        txt = d.strftime("%a %d %b %Y")
        self._date_var.set(txt)

    def set_rank(self, text: str):
        self._rank_var.set(text)

    def set_nav_enabled(self, prev_ok: bool, next_ok: bool):
        self.prev_btn.enable(bool(prev_ok))
        self.next_btn.enable(bool(next_ok))

    # Back-compat if the app calls these:
    def set_prev_enabled(self, ok: bool):
        self.prev_btn.enable(bool(ok))

    def set_next_enabled(self, ok: bool):
        self.next_btn.enable(bool(ok))

    def set_currency(self, coins: int, shards: int):
        try:
            self._coins_var.set(str(int(coins)))
        except Exception:
            self._coins_var.set("0")
        try:
            self._shards_var.set(str(int(shards)))
        except Exception:
            self._shards_var.set("0")
