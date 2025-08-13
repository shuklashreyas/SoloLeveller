import tkinter as tk
from constants import COLORS, FONTS
from widgets import RoundButton

class JournalPanel(tk.Frame):
    def __init__(self, master, on_save):
        super().__init__(master, bg=COLORS["CARD"], bd=0, highlightthickness=0)
        self.on_save = on_save

        # Header with title (left) and daily prompt (right)
        header = tk.Frame(self, bg=COLORS["CARD"])
        header.pack(fill="x", padx=12, pady=(10, 0))

        tk.Label(header, text="Journal", font=FONTS["h2"],
                 bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(side="left")

        self.prompt_lbl = tk.Label(
            header, text="", font=FONTS["small"],
            bg=COLORS["CARD"], fg=COLORS.get("MUTED", COLORS["TEXT"]),
            wraplength=520, justify="right"
        )
        self.prompt_lbl.pack(side="right")

        # Smaller text area
        self.text = tk.Text(
            self, height=6, wrap="word",
            bg=COLORS["WHITE"], fg=COLORS["TEXT"],
            highlightthickness=0, relief="flat", font=("Helvetica", 13),
            insertbackground=COLORS["PRIMARY"],  # caret color
            insertwidth=2,                        # thicker caret
            insertofftime=250, insertontime=600   # blink timing
        )
        self.text.pack(fill="both", expand=True, padx=12, pady=(6, 8))

        # Action bar
        bar = tk.Frame(self, bg=COLORS["CARD"])
        bar.pack(fill="x", padx=12, pady=(0, 12))

        self.status_label = tk.Label(bar, text="", bg=COLORS["CARD"], fg=COLORS["TEXT"], font=FONTS["small"])
        self.status_label.pack(side="left")

        self.save_btn = RoundButton(
            bar, "Save Journal",
            fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["WHITE"], padx=16, pady=8, radius=12,
            command=self._save
        )
        self.save_btn.pack(side="right")

    # ---- API ----
    def set_prompt(self, text: str):
        """Set the daily prompt (from journal_prompts.txt)."""
        self.prompt_lbl.config(text=text or "")

    def set_text(self, text, editable: bool):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text or "")
        if editable:
            self.text.config(state="normal")
            self.text.focus_set()            # show caret where user will type
            self.save_btn.enable(True)
            self.status_label.config(text="")
        else:
            self.text.config(state="disabled")
            self.save_btn.enable(False)
            self.status_label.config(text="(view-only for past/future dates)")

    def _save(self):
        # strip trailing newline Tk adds at end
        content = self.text.get("1.0", "end-1c")
        self.on_save(content)

    def note_saved(self):
        self.status_label.config(text="Saved.")
