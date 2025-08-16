import tkinter as tk
from tkinter import messagebox
from datetime import date
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

        # Smaller text area (reduced height)
        self.text = tk.Text(
            self, height=3, wrap="word",
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

        # ---- Shop area (under journal) ----
        shop_frame = tk.Frame(self, bg=COLORS["CARD"], bd=0)
        shop_frame.pack(fill="x", padx=12, pady=(6, 12))

        tk.Label(shop_frame, text="Shop", font=FONTS["h3"], bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w")
        self._shop_row = tk.Frame(shop_frame, bg=COLORS["CARD"]) ; self._shop_row.pack(fill="x", pady=(6,0))

        # Load tokens and show three random items
        try:
            import csv, random, json
            from pathlib import Path
            tokens = []
            tokp = Path("data/shop_tokens.csv")
            if tokp.exists():
                with tokp.open(encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        tokens.append(r)
            choices = random.sample(tokens, min(3, len(tokens))) if tokens else []
        except Exception:
            choices = []

        # Simple inventory save
        inv_path = Path("data/shop_inventory.json")

        def _buy(tok):
            try:
                from shop.currency import add_coins
                cost = int(tok.get("cost_amount") or 0)
                currency = (tok.get("cost_currency") or "coins").lower()
                if currency != "coins":
                    messagebox.showinfo("Shop", "Only coins supported for now.", parent=self)
                    return
                applied = add_coins(-cost)
                if applied == 0:
                    messagebox.showinfo("Shop", "Not enough coins.", parent=self)
                    return
                # persist
                items = []
                try:
                    if inv_path.exists():
                        items = json.loads(inv_path.read_text(encoding="utf-8") or "[]")
                except Exception:
                    items = []
                items.append({"item": tok.get("item"), "category": tok.get("category"), "bought_at": str(date.today())})
                inv_path.write_text(json.dumps(items), encoding="utf-8")
                messagebox.showinfo("Shop", f"Bought {tok.get('item')}", parent=self)
            except Exception:
                messagebox.showinfo("Shop", "Purchase failed.", parent=self)

        for i, tok in enumerate(choices):
            frm = tk.Frame(self._shop_row, bg=COLORS["CARD"], bd=0)
            frm.pack(side="left", padx=8)
            # token image if available
            img_path = Path(f"images/token{i+1}.png")
            if img_path.exists():
                try:
                    img = tk.PhotoImage(file=str(img_path))
                    # If the image is large, subsample it so it fits the journal UI.
                    # Aim for a maximum dimension of ~48px for token previews.
                    try:
                        max_size = 48
                        w, h = img.width(), img.height()
                        if w > max_size or h > max_size:
                            factor = max(1, int(max(w // max_size, h // max_size)))
                            img = img.subsample(factor, factor)
                    except Exception:
                        # If subsample or size checks fail, fall back to the original image.
                        pass
                    lbl_img = tk.Label(frm, image=img, bg=COLORS["CARD"]) ; lbl_img.image = img
                    lbl_img.pack()
                except Exception:
                    pass
            tk.Label(frm, text=tok.get("item"), bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack()
            tk.Label(frm, text=f"{tok.get('duration','')}", bg=COLORS["CARD"], fg=COLORS["MUTED"], font=FONTS["small"]).pack()
            b = RoundButton(frm, "Buy", fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]), fg=COLORS["WHITE"], padx=10, pady=6, radius=10, command=lambda t=tok: _buy(t))
            b.pack(pady=(6,0))

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
