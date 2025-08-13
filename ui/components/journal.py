import tkinter as tk
from constants import COLORS, FONTS
from widgets import RoundButton

class JournalPanel(tk.Frame):
    def __init__(self, master, on_save):
        super().__init__(master, bg=COLORS["CARD"], bd=0, highlightthickness=0)
        self.on_save = on_save

        tk.Label(self, text="Journal", font=FONTS["h2"],
                 bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=16, pady=(12, 4))

        self.text = tk.Text(
            self, height=10, wrap="word",
            bg=COLORS["WHITE"], fg=COLORS["TEXT"],
            highlightthickness=0, relief="flat", font=("Helvetica", 13),
            insertbackground=COLORS["PRIMARY"],  # caret color
            insertwidth=2,                        # thicker caret
            insertofftime=250, insertontime=600   # blink timing
        )
        self.text.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        bar = tk.Frame(self, bg=COLORS["CARD"]); bar.pack(fill="x", padx=12, pady=(0, 12))
        self.status_label = tk.Label(bar, text="", bg=COLORS["CARD"], fg=COLORS["TEXT"], font=FONTS["small"])
        self.status_label.pack(side="left")
        self.save_btn = RoundButton(bar, "Save Journal",
                                    fill=COLORS["PRIMARY"], hover_fill="#7A71FF",
                                    fg=COLORS["WHITE"], padx=16, pady=8, radius=12,
                                    command=self._save)
        self.save_btn.pack(side="right")

    def set_text(self, text, editable: bool):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        if editable:
            self.text.config(state="normal")
            self.text.focus_set()            # <-- show caret where user will type
            self.save_btn.enable(True)
            self.status_label.config(text="")
        else:
            self.text.config(state="disabled")
            self.save_btn.enable(False)
            self.status_label.config(text="(view-only for past/future dates)")

    def _save(self):
        self.on_save(self.text.get("1.0", "end"))

    def note_saved(self):
        self.status_label.config(text="Saved.")
