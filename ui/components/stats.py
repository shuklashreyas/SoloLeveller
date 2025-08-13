# ui/components/stats.py
import tkinter as tk
from constants import COLORS, FONTS, POSITIVE_TRAITS, STAT_MIN, STAT_MAX

BAR_H = 12
RADIUS = 6
BAR_WIDTH = 320

class _Bar(tk.Canvas):
    def __init__(self, master, width=BAR_WIDTH):
        super().__init__(master, width=width, height=BAR_H, bg=COLORS["CARD"],
                         highlightthickness=0, bd=0)
        self.w = width

    def _rounded_rect(self, x1, y1, x2, y2, r, fill):
        pts = [
            x1+r,y1, x2-r,y1, x2,y1, x2,y1+r,
            x2,y2-r, x2,y2, x2-r,y2, x1+r,y2,
            x1,y2, x1,y2-r, x1,y1+r, x1,y1
        ]
        self.create_polygon(pts, smooth=True, splinesteps=36, fill=fill, outline="")

    def draw(self, value, baseline):
        self.delete("all")
        # Track
        self._rounded_rect(0, 0, self.w, BAR_H, RADIUS, fill=COLORS.get("TRACK", "#D4D4D8"))

        # Baseline segment (neutral)
        base_px = max(0, min(self.w, int(self.w * baseline / STAT_MAX)))
        cur_px  = max(0, min(self.w, int(self.w * value    / STAT_MAX)))

        if base_px > 0:
            self._rounded_rect(0, 0, base_px, BAR_H, RADIUS, fill="#BFC8D4")

        # Delta overlay
        if cur_px != base_px:
            if cur_px > base_px:
                self._rounded_rect(base_px, 0, cur_px, BAR_H, RADIUS, fill=COLORS.get("GOOD", "#22C55E"))
            else:
                self._rounded_rect(cur_px, 0, base_px, BAR_H, RADIUS, fill=COLORS.get("BAD", "#EF4444"))

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

            bar = _Bar(row, width=BAR_WIDTH)
            bar.pack(side="left", padx=8, fill="x", expand=True)

            val_lbl = tk.Label(row, text=str(STAT_MIN), font=FONTS["body"],
                               bg=COLORS["CARD"], fg=COLORS["PRIMARY"], width=4)
            val_lbl.pack(side="left", padx=6)

            self.rows[trait] = {
                "bar": bar,
                "lbl": val_lbl,
                "baseline": STAT_MIN,
                "current": STAT_MIN,
            }

    def set_baselines(self, baseline_map: dict):
        """Set per-trait baselines (used for green/red delta)."""
        for t, base in baseline_map.items():
            if t in self.rows:
                try:
                    self.rows[t]["baseline"] = int(base)
                except Exception:
                    pass
        # redraw with current values against new baselines
        for t, data in self.rows.items():
            data["bar"].draw(data["current"], data["baseline"])

    def set_value(self, trait, *args):
        """
        Accepts either:
          set_value(trait, new_val)
        or
          set_value(trait, old_val, new_val)  # old_val ignored (kept for compatibility)
        """
        if trait not in self.rows:
            return
        if len(args) == 1:
            new_val = int(args[0])
        elif len(args) == 2:
            # old_val, new_val = args  # old_val not needed for drawing here
            new_val = int(args[1])
        else:
            raise TypeError("set_value expects (trait, new_val) or (trait, old_val, new_val)")

        self.rows[trait]["current"] = new_val
        self.rows[trait]["lbl"].config(text=str(new_val))
        base = self.rows[trait]["baseline"]
        self.rows[trait]["bar"].draw(new_val, base)
