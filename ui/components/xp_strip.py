import tkinter as tk
from tkinter import ttk
from constants import COLORS


class XPStrip(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=COLORS["BG"])
        self.level_label = tk.Label(
            self,
            text="LVL 1",
            font=("Helvetica", 13, "bold"),
            bg=COLORS["BG"],
            fg=COLORS["TEXT"],
        )
        self.level_label.pack(side="left", padx=12)

        self.var = tk.IntVar(value=0)
        self.bar = ttk.Progressbar(
            self,
            orient="horizontal",
            mode="determinate",
            variable=self.var,
            maximum=100,
            style="XP.Horizontal.TProgressbar",
            length=640,
        )
        self.bar.pack(side="left", padx=8, fill="x", expand=True)

        self.text = tk.Label(
            self, text="0/100 XP", font=("Helvetica", 11), bg=COLORS["BG"], fg=COLORS["TEXT"]
        )
        self.text.pack(side="left", padx=8)

        # small boost delta label (hidden when empty)
        self.boost_label = tk.Label(
            self, text="", font=("Helvetica", 10, "bold"), bg=COLORS["BG"], fg="#4CAF50"
        )
        self.boost_label.pack(side="left", padx=6)

    # no scheduled clear by default

    def set_level(self, lvl, in_level, need, animate_from=None):
        self.level_label.config(text=f"LVL {lvl}")
        self.bar.configure(maximum=need)
        if animate_from is not None:
            # simple tween to avoid pulling in animations module here
            step = 1 if in_level >= animate_from else -1
            val = animate_from
            self.var.set(val)

            def tick():
                nonlocal val
                if val == in_level:
                    return
                val += step
                self.var.set(val)
                self.after(6, tick)

            tick()
        else:
            self.var.set(in_level)
        self.text.config(text=f"{in_level}/{need} XP")

    def set_boost_info(self, text: str | None):
        """Display a small boost info string (e.g. '+4 XP' or '+25%').

        When a non-empty string is provided the label is shown and cleared after
        a short timeout (2500 ms). Subsequent calls refresh the timeout.
        """
        try:
            if text:
                self.boost_label.config(text=str(text))
                self.boost_label.lift()
            else:
                self.boost_label.config(text="")
        except Exception:
            pass
