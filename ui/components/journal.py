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
    def _rebind_buy_button(self, slot, tok, buy_func):
        """Safely rebind the Buy button to call buy_func(tok)."""
        try:
            slot["buy_btn"].set_command(lambda t=tok: buy_func(t))
            return
        except Exception:
            pass
        parent = slot["buy_btn"].master if slot.get("buy_btn") else slot["frame"]
        try:
            slot["buy_btn"].destroy()
        except Exception:
            pass
        btn = RoundButton(
            parent, "Buy",
            fill=COLORS["PRIMARY"],
            hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["WHITE"],
            padx=10, pady=6, radius=10,
            command=lambda t=tok: buy_func(t)
        )
        btn.pack(pady=(6, 0))
        slot["buy_btn"] = btn

    def __init__(self, master, on_save):
        super().__init__(master, bg=COLORS["CARD"], bd=0, highlightthickness=0)
        self.on_save = on_save

        # ---------- Category normalization + icon loading ----------
        def _norm(s):  # local helper visible to nested funcs
            return (s or "").strip().lower()



        self._live_images = []            # keep strong refs so PhotoImage isn't GC'd
        self._icon_by_category = {}       # normalized category -> PhotoImage
        self._icon_list = []              # [token1..token6] in order for fallback

        images_dir = Path(__file__).resolve().parents[2] / "images"

        # Load currency icons
        self._currency_icons = {}
        for name in ["coin", "shard"]:
            icon = None
            try:
                orig_icon = tk.PhotoImage(file=str(images_dir / f"{name}.png"))
                # Subsample to make it smaller for the label (e.g., 24x24 or less)
                w, h = orig_icon.width(), orig_icon.height()
                factor = max(1, int(max(w, h) / 20))
                if factor > 1:
                    icon = orig_icon.subsample(factor, factor)
                else:
                    icon = orig_icon
                self._live_images.append(icon)
            except Exception:
                pass
            self._currency_icons[name] = icon


        def _load_png(fname, max_wh=48):
            p = images_dir / fname
            if not p.exists():
                print(f"[shop.img] missing {p}")
                return None
            try:
                img = tk.PhotoImage(file=str(p))
                # integer subsample down if needed (Tk limitation)
                try:
                    w, h = img.width(), img.height()
                    if max(w, h) > max_wh:
                        factor = max(1, int(math.ceil(max(w, h) / max_wh)))
                        img = img.subsample(factor, factor)
                except Exception:
                    pass
                self._live_images.append(img)
                print(f"[shop.img] loaded {fname} ({img.width()}x{img.height()})")
                return img
            except Exception as e:
                print(f"[shop.img] fail {p}: {e}")
                return None

        # Load the six token icons (some may be None if missing)
        for i in range(1, 7):
            self._icon_list.append(_load_png(f"token{i}.png"))

        # Canonical category mapping (normalized keys)
        self._icon_by_category[_norm("Boosts")] = self._icon_list[0]
        self._icon_by_category[_norm("Neglects")] = self._icon_list[1]
        self._icon_by_category[_norm("Contracts & Offers")] = self._icon_list[2]
        self._icon_by_category[_norm("Logger")] = self._icon_list[3]
        self._icon_by_category[_norm("Random Challenge helpers")] = self._icon_list[4]
        self._icon_by_category[_norm("Utility & QoL")] = self._icon_list[5]

        # ---------- Header ----------
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
            insertbackground=COLORS["PRIMARY"],
            insertwidth=2,
            insertofftime=250, insertontime=600
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


        # ---------- Shop area ----------
        shop_frame = tk.Frame(self, bg=COLORS["CARD"], bd=0)
        shop_frame.pack(fill="x", padx=12, pady=(6, 12))

        tk.Label(shop_frame, text="Shop", font=FONTS["h3"], bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w")
        self._shop_row = tk.Frame(shop_frame, bg=COLORS["CARD"])
        self._shop_row.pack(fill="x", pady=(6, 0))



        # Place My Items button on the action bar (right, next to Save Journal)
        def _show_inventory_popup():
            win = tk.Toplevel(self)
            win.title("Inventory")
            win.configure(bg=COLORS["CARD"])
            tk.Label(win, text="Inventory", font=FONTS["h3"], bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=12, pady=(12, 0))

            # --- Scrollable frame setup ---
            outer = tk.Frame(win, bg=COLORS["CARD"])
            outer.pack(fill="both", expand=True, padx=12, pady=(6, 12))
            canvas = tk.Canvas(outer, bg=COLORS["CARD"], highlightthickness=0, bd=0, width=420, height=320)
            scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
            scroll_frame = tk.Frame(canvas, bg=COLORS["CARD"])
            scroll_frame_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            def _on_frame_configure(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
            scroll_frame.bind("<Configure>", _on_frame_configure)

            # --- Inventory content ---
            inv_path = Path("data/shop_inventory.json")
            items = []
            try:
                if inv_path.exists():
                    items = json.loads(inv_path.read_text(encoding="utf-8") or "[]")
            except Exception:
                items = []
            if not items:
                tk.Label(scroll_frame, text="No tokens owned.", bg=COLORS["CARD"], fg=COLORS["MUTED"]).pack()
            else:
                tokens = []
                tokp = Path("data/shop_tokens.csv")
                try:
                    if tokp.exists():
                        with tokp.open(encoding="utf-8") as f:
                            for r in csv.DictReader(f):
                                tokens.append(r)
                except Exception:
                    pass
                for entry in items:
                    name = entry.get("item")
                    tok = next((t for t in tokens if t.get("item") == name), None)
                    if not tok:
                        continue
                    cat_norm = (tok.get("category") or "").strip().lower()
                    img = self._icon_by_category.get(cat_norm)
                    if not img:
                        idx = abs(hash(cat_norm)) % max(1, len(self._icon_list))
                        img = self._icon_list[idx]
                    row = tk.Frame(scroll_frame, bg=COLORS["CARD"])
                    row.pack(fill="x", pady=2)
                    if img:
                        icon_lbl = tk.Label(row, image=img, bg=COLORS["CARD"])
                        icon_lbl.image = img
                        icon_lbl.pack(side="left", padx=(0, 8))
                    desc = tok.get("effect") or "No description."
                    tk.Label(row, text=name, font=(None, 11, "bold"), bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(side="left")
                    tk.Label(row, text=desc, font=(None, 10), bg=COLORS["CARD"], fg=COLORS["MUTED"], wraplength=260, justify="left").pack(side="left", padx=(8, 0))

            RoundButton(win, "Close", fill=COLORS["PRIMARY"], fg=COLORS["WHITE"], command=win.destroy, padx=10, pady=6, radius=8).pack(pady=(0, 12))

        my_items_btn = RoundButton(bar, "My Items", fill=COLORS["PRIMARY"], fg=COLORS["WHITE"], command=_show_inventory_popup, padx=12, pady=6, radius=10)
        my_items_btn.pack(side="right", padx=(0, 8))


        # Load token definitions
        tokens = []
        tokp = Path("data/shop_tokens.csv")
        try:
            if tokp.exists():
                with tokp.open(encoding="utf-8") as f:
                    for r in csv.DictReader(f):
                        tokens.append(r)
        except Exception as e:
            print(f"[shop] could not read {tokp}: {e}")
        choices = random.sample(tokens, min(3, len(tokens))) if tokens else []
        print(f"[shop] loaded {len(tokens)} tokens, initial choices: {len(choices)}")

        # Inventory / slots persistence
        inv_path = Path("data/shop_inventory.json")
        slots_path = Path("data/shop_slots.json")

        def _save_slots_state():
            try:
                out = []
                for s in self._shop_slots:
                    tok = s.get("tok")
                    if not tok:
                        out.append(None); continue
                    exp = s.get("expires_at")
                    out.append({"item": tok.get("item"),
                                "expires_at": exp.isoformat() if exp else None})
                slots_path.parent.mkdir(parents=True, exist_ok=True)
                slots_path.write_text(json.dumps(out), encoding="utf-8")
            except Exception:
                pass

        def _load_slots_state():
            try:
                if not slots_path.exists():
                    return []
                return json.loads(slots_path.read_text(encoding="utf-8") or "[]")
            except Exception:
                return []

        def _buy(tok):
            try:
                from shop.currency import add_coins, add_shards
                cost = int(tok.get("cost_amount") or 0)
                currency = (tok.get("cost_currency") or "coins").strip().lower()
                if "shard" in currency:
                    applied = add_shards(-cost)
                    if applied == 0:
                        messagebox.showinfo("Shop", "Not enough shards.", parent=self)
                        return
                elif "coin" in currency:
                    applied = add_coins(-cost)
                    if applied == 0:
                        messagebox.showinfo("Shop", "Not enough coins.", parent=self)
                        return
                else:
                    messagebox.showinfo("Shop", f"Currency '{currency}' not supported.", parent=self)
                    return
                # persist
                items = []
                try:
                    if inv_path.exists():
                        items = json.loads(inv_path.read_text(encoding="utf-8") or "[]")
                except Exception:
                    items = []
                items.append({
                    "item": tok.get("item"),
                    "category": tok.get("category"),
                    "bought_at": str(date.today())
                })

                inv_path.write_text(json.dumps(items), encoding="utf-8")

                # Play bought sound effect
                try:
                    from sound import play_sfx
                    play_sfx("soundeffects/bought.mp3")
                except Exception:
                    pass

                # Update currency display if method exists
                try:
                    if hasattr(self.master, "update_currency_display"):
                        self.master.update_currency_display()
                except Exception:
                    pass

                messagebox.showinfo("Shop", f"Bought {tok.get('item')}", parent=self)

                # Find the slot for this token
                slot = next((s for s in self._shop_slots if s.get("tok") == tok), None)
                if slot:
                    # Fade out animation for the slot's holder
                    steps = 10
                    def fade(step=0):
                        if step > steps:
                            # After fade, replace slot
                            _replace_slot(slot)
                            return
                        # Calculate new color (simple fade to CARD bg)
                        try:
                            alpha = 1.0 - (step / steps)
                            # Simulate fade by adjusting fg/bg of all children
                            for child in slot["holder"].winfo_children():
                                try:
                                    child.configure(bg=COLORS["CARD"])
                                except Exception:
                                    pass
                            slot["holder"].update_idletasks()
                        except Exception:
                            pass
                        slot["holder"].after(30, fade, step + 1)
                    fade()
            except Exception:
                messagebox.showinfo("Shop", "Purchase failed.", parent=self)

        # --- Slot UI helpers ---
        self._shop_slots = []

        def _show_slot_info(slot):
            try:
                t = slot.get("tok") or {}
                print(f"[shop] token clicked: {t.get('item') if t else '<empty>'}")
                try:
                    from sound import play_sfx
                    play_sfx("click")
                except Exception:
                    pass

                info = tk.Toplevel(self)
                info.transient(self)
                info.title(t.get("item") or "Token")
                info.configure(bg=COLORS.get("CARD", "#fff"))
                # Show icon if available
                cat_norm = (t.get("category") or "").strip().lower()
                img = self._icon_by_category.get(cat_norm)
                if not img:
                    idx = abs(hash(cat_norm)) % max(1, len(self._icon_list))
                    img = self._icon_list[idx]
                if img:
                    icon_lbl = tk.Label(info, image=img, bg=COLORS.get("CARD", "#fff"))
                    icon_lbl.image = img
                    icon_lbl.pack(pady=(12, 0))
                txt = t.get("description") or t.get("details") or t.get("item") or "No description available."
                tk.Label(info, text=txt, wraplength=320,
                         bg=COLORS.get("CARD", "#fff"),
                         fg=COLORS.get("TEXT", "#000"), font=(None, 11)).pack(padx=12, pady=12)
                RoundButton(info, "Close", fill=COLORS["PRIMARY"], fg=COLORS["WHITE"],
                            command=info.destroy, padx=10, pady=6, radius=8).pack(pady=(0, 12))
                try:
                    info.update_idletasks(); info.lift(); info.attributes("-topmost", True)
                    info.grab_set(); info.focus_force()
                    info.after(150, lambda w=info: w.attributes("-topmost", False))
                except Exception:
                    pass
            except Exception:
                return


        def _make_slot(idx, initial_tok=None):
            frm = tk.Frame(self._shop_row, bg=COLORS["CARD"], bd=0)
            frm.pack(side="left", padx=4)

            holder = tk.Frame(frm, width=96, height=80, bg=COLORS["CARD"])
            holder.pack()
            holder.pack_propagate(False)

            # placeholder glyph so area is visible before image loads
            ph = tk.Label(holder, text="◇", font=(None, 12),
                          bg=COLORS["CARD"], fg=COLORS["MUTED"])
            ph.place(relx=0.5, rely=0.5, anchor='center')

            item_lbl  = tk.Label(frm, text="", bg=COLORS["CARD"], fg=COLORS["TEXT"], font=(None, 9, "bold")); item_lbl.pack()
            dur_lbl   = tk.Label(frm, text="", bg=COLORS["CARD"], fg=COLORS["MUTED"], font=(None, 8)); dur_lbl.pack()
            timer_lbl = tk.Label(frm, text="", bg=COLORS["CARD"], fg=COLORS["PRIMARY"], font=(None, 8)); timer_lbl.pack()

            buy_btn = RoundButton(frm, "Buy",
                                  fill=COLORS["PRIMARY"],
                                  hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                                  fg=COLORS["WHITE"], padx=6, pady=3, radius=8,
                                  command=lambda: None)
            buy_btn.pack(pady=(4, 0))

            slot = {
                "idx": idx, "frame": frm, "holder": holder,
                "img_label": None, "item_lbl": item_lbl, "dur_lbl": dur_lbl,
                "timer_lbl": timer_lbl, "buy_btn": buy_btn,
                "tok": None, "expires_at": None,
            }

            frm.bind("<Button-1>", lambda e, s=slot: _show_slot_info(s))
            frm.config(cursor="hand2")

            if initial_tok:
                _assign_token_to_slot(slot, initial_tok)
            return slot


        def _assign_token_to_slot(slot, tok, expires_at=None):
            """Assign token to slot; handle expiry and image."""
            print(f"[shop.trace] assign -> slot {slot.get('idx')} item={tok.get('item')!r}")
            slot["tok"] = tok

            # expiry
            try:
                if expires_at:
                    if isinstance(expires_at, str):
                        slot["expires_at"] = datetime.fromisoformat(expires_at)
                    elif isinstance(expires_at, datetime):
                        slot["expires_at"] = expires_at
                    else:
                        slot["expires_at"] = datetime.now() + timedelta(seconds=int(expires_at))
                else:
                    slot["expires_at"] = datetime.now() + timedelta(seconds=random.choice([3600, 5*3600, 2*24*3600]))
            except Exception:
                slot["expires_at"] = datetime.now() + timedelta(seconds=random.choice([3600, 5*3600, 2*24*3600]))

            # labels + buy
            # Show cost with currency icon
            cost = tok.get("cost_amount", "")
            currency = (tok.get("cost_currency") or "Coins").strip().lower()
            icon = None
            if "shard" in currency:
                icon = self._currency_icons.get("shard")
            elif "coin" in currency:
                icon = self._currency_icons.get("coin")
            # Compose label with icon and text
            if icon:
                slot["item_lbl"].config(image=icon, compound="left", text=f" {cost}", font=(None, 11, "bold"), fg=COLORS["TEXT"], bg=COLORS["CARD"])
                slot["item_lbl"].image = icon
            else:
                slot["item_lbl"].config(text=f"{cost} {currency.title()}", image="", font=(None, 11, "bold"), fg=COLORS["TEXT"], bg=COLORS["CARD"])
            slot["dur_lbl"].config(text=f"{tok.get('duration','')}")
            self._rebind_buy_button(slot, tok, _buy)

            # clear holder
            for child in slot["holder"].winfo_children():
                try: child.destroy()
                except: pass

            # choose image by category (as you had)
            cat_norm = (tok.get("category") or "").strip().lower()
            img = self._icon_by_category.get(cat_norm)
            if not img:
                idx = abs(hash(cat_norm)) % max(1, len(self._icon_list))
                img = self._icon_list[idx]
                print(f"[shop.img] fallback icon for '{tok.get('category')}' -> token{idx+1}.png")

            # size to holder
            try:
                W = int(slot["holder"].cget("width"))
                H = int(slot["holder"].cget("height"))
            except Exception:
                W, H = 96, 80


            if img:
                img_frame = tk.Frame(slot["holder"], width=W, height=H, bg=COLORS["CARD"], bd=0, highlightthickness=0)
                img_frame.place(relx=0.5, rely=0.5, anchor='center')
                img_frame.pack_propagate(False)

                # Define click handlers before creating widgets so they close over the right slot/tok
                def _on_click(event=None, t=tok, s=slot):
                    _show_slot_info(s)
                def _wrapped_on_click(event=None, t=tok, s=slot):
                    try:
                        if event is not None and hasattr(event, "widget"):
                            w = event.widget
                            if w == s.get("buy_btn") or getattr(w, "master", None) == s.get("buy_btn"):
                                return
                    except Exception:
                        pass
                    return _on_click(event, t, s)

                lbl = tk.Label(img_frame, image=img, bg=COLORS["CARD"], bd=0, padx=0, pady=0, width=img.width(), height=img.height())
                lbl.image = img
                lbl.pack(side="top", anchor="center", pady=(8, 0))
                # Make the image itself clickable
                try:
                    lbl.bind("<Button-1>", _wrapped_on_click)
                    lbl.config(cursor="hand2")
                except Exception:
                    pass

                # Name badge inside the same frame (centered, wrapped)
                name = (tok.get("item") or "")
                short = name if len(name) <= 24 else name[:22] + "…"
                badge = tk.Label(
                    img_frame,
                    text=short,
                    bg=COLORS["CARD"],
                    fg=COLORS.get("TEXT", "#000"),
                    font=(None, 8, "bold"),
                    anchor="center",
                    justify="center",
                    wraplength=W - 8,   # keep inside holder
                    padx=3
                )
                badge.pack(side="bottom", anchor="center", pady=(2, 4), fill="x")
                slot["name_badge"] = badge

                # Gentle bob for the whole frame (keeps image+badge together)
                img_frame._phase = random.uniform(0, 2 * math.pi)  # randomize phase for out-of-sync bob
                amplitude = max(3, min(10, (H - 100) // 3))  # stay within holder
                step_ms = 80
                def _bob(widget):
                    try:
                        widget._phase += 0.25
                        y = int(amplitude * math.sin(widget._phase))
                        widget.place_configure(relx=0.5, rely=0.5, anchor='center', y=y)
                        widget.after(step_ms, _bob, widget)
                    except Exception:
                        pass
                _bob(img_frame)

                slot["img_label"] = img_frame
            else:
                # fallback blank
                blank = tk.Frame(slot["holder"], width=W, height=H, bg=COLORS["CARD"], bd=0, highlightthickness=0)
                blank.place(relx=0.5, rely=0.5, anchor='center')
                slot["img_label"] = blank

            # click handlers (don’t steal clicks from Buy)
            def _on_click(event=None, t=tok, s=slot):
                _show_slot_info(s)
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

            _save_slots_state()

        def _replace_slot(slot):
            pool = [t for t in tokens if t and t != slot.get("tok")] or tokens[:]
            new_tok = random.choice(pool) if pool else None
            if new_tok:
                _assign_token_to_slot(slot, new_tok)
                _save_slots_state()

        # create up to 3 visible slots, try to restore previous state
        visible = min(3, max(1, len(tokens))) or 3
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
                            _assign_token_to_slot(slot, restored, expires_at=entry.get("expires_at"))
            if not restored:
                if i < len(choices):
                    _assign_token_to_slot(slot, choices[i])
                elif tokens:
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
                    _replace_slot(slot); continue
                if remaining >= 86400:
                    text = f"{remaining // 86400}d"
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
            self.after(1000, _update_timers)

        self.after(1000, _update_timers)

    # ---- Public API ----
    def set_prompt(self, text: str):
        self.prompt_lbl.config(text=text or "")

    def set_text(self, text, editable: bool):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text or "")
        if editable:
            self.text.config(state="normal")
            self.text.focus_set()
            self.save_btn.enable(True)
            self.status_label.config(text="")
        else:
            self.text.config(state="disabled")
            self.save_btn.enable(False)
            self.status_label.config(text="(view-only for past/future dates)")

    def _save(self):
        content = self.text.get("1.0", "end-1c")
        self.on_save(content)

    def note_saved(self):
        self.status_label.config(text="Saved.")
