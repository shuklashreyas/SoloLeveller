import tkinter as tk
from tkinter import messagebox
from datetime import date, datetime, timedelta
import math
from pathlib import Path
import random
import json
import csv
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

        # Load tokens and show three random items. Each token gets a random expiry
        # (1 hr, 5 hrs, or 2 days). When a token expires it's replaced with a new one.
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
            # initial choices (may be fewer than 3)
            choices = random.sample(tokens, min(3, len(tokens))) if tokens else []
            print(f"[shop] loaded {len(tokens)} tokens, initial choices: {len(choices)}")
        except Exception:
            tokens = []
            choices = []

        # Simple inventory save
        inv_path = Path("data/shop_inventory.json")
        # Persistent shop slots (so tokens survive restarts until expiry)
        slots_path = Path("data/shop_slots.json")

        # Load token images once (after Tk root exists). Use absolute project-relative images/ path.
        self._token_images = []
        try:
            images_dir = Path(__file__).parent.parent.parent / "images"
            for i in range(1, 7):
                p = images_dir / f"token{i}.png"
                if p.exists():
                    try:
                        img = tk.PhotoImage(file=str(p))
                        # scale down if too large
                        try:
                            max_size = 48
                            w, h = img.width(), img.height()
                            if w > max_size or h > max_size:
                                factor = max(1, int(max(w / max_size, h / max_size)))
                                img = img.subsample(factor, factor)
                        except Exception:
                            pass
                        self._token_images.append(img)
                    except Exception:
                        self._token_images.append(None)
                else:
                    self._token_images.append(None)
        except Exception:
            # fallback: empty list of images
            self._token_images = [None] * 6

        def _save_slots_state():
            try:
                out = []
                for s in self._shop_slots:
                    tok = s.get("tok")
                    if not tok:
                        out.append(None)
                        continue
                    exp = s.get("expires_at")
                    out.append({
                        "item": tok.get("item"),
                        "expires_at": exp.isoformat() if exp else None,
                    })
                slots_path.parent.mkdir(parents=True, exist_ok=True)
                slots_path.write_text(json.dumps(out), encoding="utf-8")
            except Exception:
                pass

        def _load_slots_state():
            try:
                if not slots_path.exists():
                    return []
                data = json.loads(slots_path.read_text(encoding="utf-8") or "[]")
                return data
            except Exception:
                return []

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

        # We'll create up to 3 slots and manage their timers/expiry.
        self._shop_slots = []
        slot_count = max(3, len(choices)) if choices else 3
        # Helper to create/replace slot content
        def _show_slot_info(slot):
            try:
                t = slot.get("tok") or {}
                print(f"[shop] token clicked: {t.get('item') if t else '<empty>'}")
                # play click sound if available
                try:
                    from sound import play_sfx
                    play_sfx("click")
                except Exception:
                    pass
                # visual flash
                try:
                    frm = slot.get("frame")
                    if frm:
                        oldbg = frm.cget("bg")
                        frm.config(bg=COLORS.get("PRIMARY_HOVER", oldbg))
                        frm.after(180, lambda: frm.config(bg=oldbg))
                except Exception:
                    pass
                # info modal
                try:
                    info = tk.Toplevel(self)
                    info.transient(self)
                    info.title(t.get("item") or "Token")
                    info.configure(bg=COLORS.get("CARD", "#fff"))
                    txt = t.get("description") or t.get("details") or t.get("item") or "No description available."
                    lbl = tk.Label(info, text=txt, wraplength=320, bg=COLORS.get("CARD", "#fff"), fg=COLORS.get("TEXT", "#000"))
                    lbl.pack(padx=12, pady=12)
                    ok = RoundButton(info, "Close", fill=COLORS["PRIMARY"], fg=COLORS["WHITE"], command=info.destroy, padx=10, pady=6, radius=8)
                    ok.pack(pady=(0,12))

                    # Ensure the window is visible and focused on macOS/Windows.
                    try:
                        info.update_idletasks()
                        # lift and temporarily set topmost so it appears above the main window
                        info.lift()
                        info.attributes("-topmost", True)
                        info.grab_set()
                        info.focus_force()
                        # remove topmost shortly after so it doesn't stay above everything
                        info.after(150, lambda w=info: w.attributes("-topmost", False))

                        # center over parent if possible, otherwise center on screen
                        pw = self.winfo_toplevel()
                        try:
                            px = pw.winfo_rootx()
                            py = pw.winfo_rooty()
                            pw_w = pw.winfo_width()
                            pw_h = pw.winfo_height()
                            if pw_w > 10 and pw_h > 10:
                                x = px + (pw_w // 2) - (info.winfo_width() // 2)
                                y = py + (pw_h // 2) - (info.winfo_height() // 2)
                            else:
                                # fallback to screen center
                                sw = info.winfo_screenwidth()
                                sh = info.winfo_screenheight()
                                x = (sw // 2) - (info.winfo_width() // 2)
                                y = (sh // 2) - (info.winfo_height() // 2)
                        except Exception:
                            sw = info.winfo_screenwidth()
                            sh = info.winfo_screenheight()
                            x = (sw // 2) - (info.winfo_width() // 2)
                            y = (sh // 2) - (info.winfo_height() // 2)
                        info.geometry(f'+{x}+{y}')
                    except Exception:
                        pass
                except Exception:
                    pass
            except Exception:
                return

        def _make_slot(idx, initial_tok=None):
            frm = tk.Frame(self._shop_row, bg=COLORS["CARD"], bd=0)
            frm.pack(side="left", padx=8)

            # create holder for the token image; actual image will be loaded when the slot is assigned a token
            holder = tk.Frame(frm, width=64, height=72, bg=COLORS["CARD"]) ; holder.pack()
            holder.pack_propagate(False)
            # placeholder so the slot area is visible
            ph = tk.Label(holder, text="◇", font=(None, 20), bg=COLORS["CARD"], fg=COLORS["MUTED"]) ; ph.place(relx=0.5, rely=0.5, anchor='center')

            item_lbl = tk.Label(frm, text="", bg=COLORS["CARD"], fg=COLORS["TEXT"]) ; item_lbl.pack()
            dur_lbl = tk.Label(frm, text="", bg=COLORS["CARD"], fg=COLORS["MUTED"], font=FONTS["small"]) ; dur_lbl.pack()
            timer_lbl = tk.Label(frm, text="", bg=COLORS["CARD"], fg=COLORS["PRIMARY"], font=FONTS["small"]) ; timer_lbl.pack()

            buy_btn = RoundButton(frm, "Buy", fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]), fg=COLORS["WHITE"], padx=10, pady=6, radius=10, command=lambda: None)
            buy_btn.pack(pady=(6,0))

            slot = {
                "idx": idx,
                "frame": frm,
                "holder": holder,
                "img_label": None,
                "item_lbl": item_lbl,
                "dur_lbl": dur_lbl,
                "timer_lbl": timer_lbl,
                "buy_btn": buy_btn,
                "tok": None,
                "expires_at": None,
            }

            # basic click to open info even if empty
            try:
                frm.bind("<Button-1>", lambda e, s=slot: _show_slot_info(s))
                frm.config(cursor="hand2")
            except Exception:
                pass

            # debug: slot created
            try:
                print(f"[shop.debug] created slot {idx}", flush=True)
            except Exception:
                pass

            if initial_tok:
                _assign_token_to_slot(slot, initial_tok)

            return slot

        def _assign_token_to_slot(slot, tok, expires_at=None):
            """Assign a token to a slot. expires_at may be a datetime or ISO string; if None a random duration is chosen."""
            try:
                print(f"[shop.trace] _assign_token_to_slot called for slot {slot.get('idx')} tok={repr(tok)}", flush=True)
            except Exception:
                pass
            slot["tok"] = tok
            # resolve expires_at
            if expires_at:
                try:
                    if isinstance(expires_at, str):
                        slot["expires_at"] = datetime.fromisoformat(expires_at)
                    elif isinstance(expires_at, datetime):
                        slot["expires_at"] = expires_at
                    else:
                        slot["expires_at"] = datetime.now() + timedelta(seconds=int(expires_at))
                except Exception:
                    slot["expires_at"] = datetime.now() + timedelta(seconds=random.choice([3600, 5*3600, 2*24*3600]))
            else:
                dur_seconds = random.choice([3600, 5*3600, 2*24*3600])
                slot["expires_at"] = datetime.now() + timedelta(seconds=dur_seconds)

            # update labels and buy command
            try:
                slot["item_lbl"].config(text=tok.get("item") or "")
                slot["dur_lbl"].config(text=f"{tok.get('duration','')}")
                slot["buy_btn"].config(command=lambda t=tok: _buy(t))

                # clear existing holder contents
                try:
                    for child in slot["holder"].winfo_children():
                        child.destroy()
                except Exception:
                    pass

                # determine which image to use (map 6 types into 3 images cyclically)
                img_idx = 1
                try:
                    if tokens and tok in tokens:
                        pos = tokens.index(tok)
                        img_idx = (pos % 3) + 1
                    else:
                        typ = (tok.get("type") or tok.get("category") or "0")
                        try:
                            img_idx = (int(typ) % 3) + 1
                        except Exception:
                            img_idx = 1
                except Exception:
                    img_idx = 1

                img_path = Path(f"images/token{img_idx}.png")
                # create a decorative circular canvas as a guaranteed visual so tokens are visible
                try:
                    deco_size = 44
                    canvas = tk.Canvas(slot["holder"], width=deco_size, height=deco_size, bg=COLORS["CARD"], highlightthickness=0)
                    # pick a color based on index so tokens differ
                    try:
                        colors = [COLORS.get("PRIMARY", "#2b6cb0"), COLORS.get("ACCENT", "#f6ad55"), COLORS.get("MUTED", "#9aa0a6")]
                        fill = colors[(img_idx - 1) % len(colors)]
                    except Exception:
                        fill = COLORS.get("PRIMARY", "#2b6cb0")
                    canvas.create_oval(2, 2, deco_size-2, deco_size-2, fill=fill, outline=fill)
                    canvas.place(relx=0.5, rely=0.5, anchor='center')
                    slot["deco"] = canvas
                except Exception:
                    pass
                # prefer cached images loaded at init
                try:
                    img = None
                    if getattr(self, "_token_images", None):
                        idx_cache = (img_idx - 1) % len(self._token_images)
                        try:
                            img = self._token_images[idx_cache]
                        except Exception:
                            img = None
                    # fallback: attempt to load from images/ path and log
                    if not img:
                        try:
                            print(f"[shop.debug] assigning '{tok.get('item')}' -> {img_path} (exists={img_path.exists()})", flush=True)
                        except Exception:
                            pass
                        if img_path.exists():
                            try:
                                img = tk.PhotoImage(file=str(img_path))
                            except Exception:
                                img = None
                    if img:
                        try:
                            # safety scaling for runtime-loaded images
                            try:
                                max_size = 48
                                w, h = img.width(), img.height()
                                if w > max_size or h > max_size:
                                    factor = max(1, int(max(w // max_size, h // max_size)))
                                    img = img.subsample(factor, factor)
                            except Exception:
                                pass
                            lbl = tk.Label(slot["holder"], image=img, bg=COLORS["CARD"]) ; lbl.image = img
                            lbl.place(relx=0.5, rely=0.5, anchor='center')
                            try:
                                lbl.lift()
                            except Exception:
                                pass
                            lbl._phase = 0.0
                            amplitude = 6
                            step_ms = 80
                            def _bob(widget):
                                try:
                                    widget._phase += 0.25
                                    y = int(amplitude * math.sin(widget._phase))
                                    widget.place_configure(relx=0.5, rely=0.5, anchor='center', y=y)
                                except Exception:
                                    return
                                widget.after(step_ms, _bob, widget)
                            _bob(lbl)
                            slot["img_label"] = lbl
                        except Exception:
                            pass
                except Exception:
                    pass

                # Always add a visible name badge inside the holder so the token is readable
                try:
                    # short name (trim long names)
                    name = (tok.get("item") or "")
                    short = name if len(name) <= 20 else name[:18] + "…"
                    badge = tk.Label(slot["holder"], text=short, bg=COLORS.get("WHITE", "#fff"), fg=COLORS.get("TEXT","#000"), font=(None, 9, "bold"))
                    badge.place(relx=0.5, rely=0.92, anchor='s')
                    slot["name_badge"] = badge
                except Exception:
                    pass

                # attach click handlers to show details
                def _on_click(event=None, t=tok, s=slot):
                    try:
                        try:
                            from sound import play_sfx
                            play_sfx("click")
                        except Exception:
                            pass
                        try:
                            frm = s.get("frame")
                            if frm:
                                oldbg = frm.cget("bg")
                                frm.config(bg=COLORS.get("PRIMARY_HOVER", oldbg))
                                frm.after(180, lambda: frm.config(bg=oldbg))
                        except Exception:
                            pass

                        print(f"[shop] token clicked: {t.get('item')}")
                        info = tk.Toplevel(self)
                        info.transient(self)
                        info.title(t.get("item") or "Token")
                        info.configure(bg=COLORS.get("CARD", "#fff"))
                        txt = t.get("description") or t.get("details") or t.get("item") or "No description available."
                        lbl = tk.Label(info, text=txt, wraplength=320, bg=COLORS.get("CARD", "#fff"), fg=COLORS.get("TEXT", "#000"))
                        lbl.pack(padx=12, pady=12)
                        ok = RoundButton(info, "Close", fill=COLORS["PRIMARY"], fg=COLORS["WHITE"], command=info.destroy, padx=10, pady=6, radius=8)
                        ok.pack(pady=(0,12))
                        try:
                            info.update_idletasks()
                            info.lift()
                            info.attributes("-topmost", True)
                            info.grab_set()
                            info.focus_force()
                            info.after(150, lambda w=info: w.attributes("-topmost", False))
                        except Exception:
                            pass
                        try:
                            pw = self.winfo_toplevel()
                            px = pw.winfo_rootx()
                            py = pw.winfo_rooty()
                            pw_w = pw.winfo_width()
                            pw_h = pw.winfo_height()
                            if pw_w > 10 and pw_h > 10:
                                x = px + (pw_w // 2) - (info.winfo_width() // 2)
                                y = py + (pw_h // 2) - (info.winfo_height() // 2)
                            else:
                                sw = info.winfo_screenwidth()
                                sh = info.winfo_screenheight()
                                x = (sw // 2) - (info.winfo_width() // 2)
                                y = (sh // 2) - (info.winfo_height() // 2)
                            info.geometry(f'+{x}+{y}')
                        except Exception:
                            pass
                    except Exception:
                        return

                def _wrapped_on_click(event=None, t=tok, s=slot):
                    try:
                        if event is not None and hasattr(event, "widget"):
                            w = event.widget
                            if w == s.get("buy_btn") or getattr(w, "master", None) == s.get("buy_btn"):
                                return
                    except Exception:
                        pass
                    return _on_click(event, t, s)

                try:
                    slot["frame"].bind("<Button-1>", _wrapped_on_click)
                    slot["frame"].config(cursor="hand2")
                except Exception:
                    pass
                if slot.get("img_label"):
                    try:
                        slot["img_label"].bind("<Button-1>", _wrapped_on_click)
                        slot["img_label"].config(cursor="hand2")
                    except Exception:
                        pass
                try:
                    slot["holder"].bind("<Button-1>", _wrapped_on_click)
                    slot["holder"].config(cursor="hand2")
                except Exception:
                    pass
                try:
                    slot["item_lbl"].bind("<Button-1>", _wrapped_on_click)
                    slot["item_lbl"].config(cursor="hand2")
                except Exception:
                    pass

            except Exception:
                pass

            # persist slots state after assignment
            try:
                _save_slots_state()
            except Exception:
                pass

        def _replace_slot(slot):
            try:
                pool = [t for t in tokens if t and t != slot.get("tok")]
                if not pool:
                    pool = tokens[:]
                new_tok = random.choice(pool) if pool else None
                if new_tok:
                    _assign_token_to_slot(slot, new_tok)
                    try:
                        _save_slots_state()
                    except Exception:
                        pass
            except Exception:
                return

        # create slots (limit to 3 visible)
        visible = min(3, max(1, len(tokens)))
        saved = _load_slots_state()
        for i in range(visible):
            slot = _make_slot(i)
            restored = None
            if i < len(saved):
                entry = saved[i]
                if entry and isinstance(entry, dict):
                    name = entry.get("item")
                    if name:
                        restored = next((t for t in tokens if t and t.get("item") == name), None)
                        if restored:
                            exp_iso = entry.get("expires_at")
                            try:
                                _assign_token_to_slot(slot, restored, expires_at=exp_iso)
                            except Exception:
                                _assign_token_to_slot(slot, restored)
            if not restored:
                if i < len(choices):
                    _assign_token_to_slot(slot, choices[i])
                else:
                    if tokens:
                        _assign_token_to_slot(slot, random.choice(tokens))
            self._shop_slots.append(slot)

        def _update_timers():
            now = datetime.now()
            for slot in list(self._shop_slots):
                exp = slot.get("expires_at")
                if not exp:
                    continue
                remaining = int((exp - now).total_seconds())
                if remaining <= 0:
                    _replace_slot(slot)
                    continue
                if remaining >= 86400:
                    days = remaining // 86400
                    text = f"{days}d"
                elif remaining >= 3600:
                    hrs = remaining // 3600
                    mins = (remaining % 3600) // 60
                    text = f"{hrs}h {mins}m"
                elif remaining >= 60:
                    mins = remaining // 60
                    secs = remaining % 60
                    text = f"{mins}m {secs}s"
                else:
                    text = f"{remaining}s"
                try:
                    slot["timer_lbl"].config(text=f"Expires in {text}")
                except Exception:
                    pass
            try:
                self.after(1000, _update_timers)
            except Exception:
                pass

        try:
            self.after(1000, _update_timers)
        except Exception:
            pass

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
