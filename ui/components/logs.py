import tkinter as tk
from tkinter import ttk
from constants import COLORS, FONTS

class LogsPanel(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=COLORS["CARD"], bd=0, highlightthickness=0)

        tk.Label(self, text="Today’s Log", font=FONTS["h2"],
                 bg=COLORS["CARD"], fg=COLORS["TEXT"])\
            .pack(anchor="w", padx=16, pady=(12, 4))

        outer = tk.Frame(self, bg=COLORS["CARD"]); outer.pack(fill="both", expand=True, padx=12, pady=8)

        # Atoned
        atone = tk.Frame(outer, bg=COLORS["CARD"]); atone.pack(side="top", fill="both", expand=True, pady=(0, 8))
        tk.Label(atone, text="Atoned", font=FONTS["h3"], bg=COLORS["CARD"], fg=COLORS["PRIMARY"]).pack(anchor="w")
        self.atone = ttk.Treeview(atone, columns=("time", "desc", "points"), show="headings", height=7)
        for col, text in (("time", "Time"), ("desc", "What"), ("points", "+XP")):
            self.atone.heading(col, text=text, anchor="center")
        self.atone.column("time", width=110, anchor="center")
        self.atone.column("desc", width=360, anchor="w")
        self.atone.column("points", width=60, anchor="e")
        self.atone.pack(fill="both", expand=True, pady=4)

        # Sinned
        sinned = tk.Frame(outer, bg=COLORS["CARD"]); sinned.pack(side="top", fill="both", expand=True, pady=(8, 0))
        tk.Label(sinned, text="Sinned", font=FONTS["h3"], bg=COLORS["CARD"], fg=COLORS["ACCENT"]).pack(anchor="w")
        self.sinned = ttk.Treeview(sinned, columns=("time", "desc", "points"), show="headings", height=7)
        for col, text in (("time", "Time"), ("desc", "What"), ("points", "−XP")):
            self.sinned.heading(col, text=text, anchor="center")
        self.sinned.column("time", width=110, anchor="center")
        self.sinned.column("desc", width=360, anchor="w")
        self.sinned.column("points", width=60, anchor="e")
        self.sinned.pack(fill="both", expand=True, pady=4)

        for t in (self.atone, self.sinned):
            t.tag_configure("odd", background="#FFFFFF")
            t.tag_configure("even", background="#F8FAFC")

    def load(self, records):
        for tree in (self.atone, self.sinned):
            for iid in tree.get_children():
                tree.delete(iid)
        ai = si = 0
        for rec in records:
            when = rec["ts"][11:16]
            desc = f"[{rec['category']}] {rec['item']}"
            pts = rec["points"]
            if rec["entry_type"] == "ATONE":
                tag = "odd" if (ai % 2 == 0) else "even"
                self.atone.insert("", "end", values=(when, desc, f"+{pts}"), tags=(tag,))
                ai += 1
            else:
                tag = "odd" if (si % 2 == 0) else "even"
                self.sinned.insert("", "end", values=(when, desc, str(pts)), tags=(tag,))
                si += 1
