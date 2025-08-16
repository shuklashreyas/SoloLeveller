# ui/components/topbar.py
import tkinter as tk
from datetime import date
import math
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

        # Load images and ensure a consistent max size (approx 28px)
        def _load_and_fit(path, max_size=28):
            try:
                img = tk.PhotoImage(file=path)
                try:
                    w, h = img.width(), img.height()
                    if w > max_size or h > max_size:
                        factor = max(1, int(max(w // max_size, h // max_size)))
                        img = img.subsample(factor, factor)
                except Exception:
                    pass
                return img
            except Exception:
                return None

        self._coin_img = _load_and_fit("images/coin.png", max_size=28)
        self._shard_img = _load_and_fit("images/shard.png", max_size=28)

        # Create holders so we can animate the icons without disturbing layout
        if self._coin_img:
            coin_holder = tk.Frame(center, width=34, height=34, bg=COLORS["BG"]) ; coin_holder.pack(side="left", padx=(6,2))
            coin_holder.pack_propagate(False)
            self._coin_label = tk.Label(coin_holder, image=self._coin_img, bg=COLORS["BG"]) ; self._coin_label.image = self._coin_img
            self._coin_label.place(relx=0.5, rely=0.5, anchor='center')
        else:
            self._coin_label = None

        coin_lbl = tk.Label(center, textvariable=self._coins_var, font=FONTS["small"], bg=COLORS["BG"], fg=COLORS["MUTED"]) ; coin_lbl.pack(side="left", padx=(2,8))

        if self._shard_img:
            shard_holder = tk.Frame(center, width=34, height=34, bg=COLORS["BG"]) ; shard_holder.pack(side="left", padx=(6,2))
            shard_holder.pack_propagate(False)
            self._shard_label = tk.Label(shard_holder, image=self._shard_img, bg=COLORS["BG"]) ; self._shard_label.image = self._shard_img
            self._shard_label.place(relx=0.5, rely=0.5, anchor='center')
        else:
            self._shard_label = None

        shard_lbl = tk.Label(center, textvariable=self._shards_var, font=FONTS["small"], bg=COLORS["BG"], fg=COLORS["MUTED"]) ; shard_lbl.pack(side="left", padx=(2,4))

        # Animations: coin bobs vertically, shard pulses (subtle scale via padding)
        try:
            # coin bob
            if self._coin_label:
                self._coin_label._phase = 0.0
                def _coin_bob():
                    try:
                        self._coin_label._phase += 0.25
                        y = int(3 * math.sin(self._coin_label._phase))
                        self._coin_label.place_configure(relx=0.5, rely=0.5, anchor='center', y=y)
                    except Exception:
                        return
                    self.after(140, _coin_bob)
                _coin_bob()

            # shard bob (gentle vertical motion with a slightly different phase)
            if self._shard_label:
                # shard uses a similar gentle bob but with a phase offset so movement feels distinct
                self._shard_label._phase = 0.9
                def _shard_bob():
                    try:
                        self._shard_label._phase += 0.25
                        y = int(3 * math.sin(self._shard_label._phase))
                        self._shard_label.place_configure(relx=0.5, rely=0.5, anchor='center', y=y)
                    except Exception:
                        return
                    self.after(140, _shard_bob)
                _shard_bob()
        except Exception:
            pass

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
