import tkinter as tk
from tkinter import ttk, messagebox  # FIX: import ttk here
from datetime import date
from constants import COLORS, FONTS
from widgets import RoundButton
from database import (
    get_available_contracts, claim_contract_offer,
    get_active_contracts_count, get_personal_active_count,
    create_personal_contract_limited,
    mark_contract_broken, mark_contract_penalty_applied,
)

def _safe_get_active_contracts(day_iso: str):
    # Runtime import so the app runs even if DB doesn’t expose this helper
    try:
        from database import get_active_contracts
        return get_active_contracts(day_iso)
    except Exception:
        return []


def open_contracts(self):
    win = tk.Toplevel(self.root)
    win.title("Contracts")
    win.configure(bg=COLORS["BG"])
    win.geometry("720x520")
    win.grab_set()

    # FIX: use ttk.Notebook, not tk.ttk.Notebook
    nb = ttk.Notebook(win)
    nb.pack(fill="both", expand=True, padx=10, pady=10)

    # ----- My Contracts -----
    tab_my = tk.Frame(nb, bg=COLORS["BG"]); nb.add(tab_my, text="My Contracts")

    header = tk.Frame(tab_my, bg=COLORS["BG"]); header.pack(fill="x", padx=8, pady=(8, 2))
    tk.Label(header, text="Active Contracts", font=FONTS["h2"],
             bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(side="left")

    list_my = tk.Frame(tab_my, bg=COLORS["BG"]); list_my.pack(fill="both", expand=True, padx=8, pady=6)

    form = tk.Frame(tab_my, bg=COLORS["CARD"]); form.pack(fill="x", padx=8, pady=(0, 10))
    tk.Label(form, text="Create personal contract (1–7 days)", font=FONTS["h3"],
             bg=COLORS["CARD"], fg=COLORS["TEXT"]).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 2))
    title_var = tk.StringVar()
    tk.Entry(form, textvariable=title_var, width=40).grid(row=1, column=0, padx=(12,8), pady=8, sticky="w")
    days_var = tk.IntVar(value=3)
    tk.Label(form, text="Days:", bg=COLORS["CARD"], fg=COLORS["TEXT"]).grid(row=1, column=1, sticky="e")
    tk.Spinbox(form, from_=1, to=7, width=5, textvariable=days_var).grid(row=1, column=2, padx=(6,12), sticky="w")

    def create_personal():
        try:
            create_personal_contract_limited(title_var.get().strip(), int(days_var.get()))
        except ValueError as e:
            messagebox.showwarning("Cannot create", str(e), parent=win); return
        title_var.set("")
        refresh_views()

    RoundButton(form, "Create",
                fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS["WHITE"], padx=14, pady=8, radius=12, command=create_personal)\
        .grid(row=1, column=3, padx=12, pady=8)

    # ----- Available Today -----
    tab_av = tk.Frame(nb, bg=COLORS["BG"]); nb.add(tab_av, text="Available Today")
    hdr_frame = tk.Frame(tab_av, bg=COLORS["BG"])
    hdr_frame.pack(fill="x", padx=8, pady=(8, 2))
    tk.Label(hdr_frame, text="Time-limited offers (claim before they expire)",
             font=FONTS["h2"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(side="left")

    def use_offer_beacon():
        try:
            from shop.effects import effects
            a = effects.dump().get('active', {})
            if int(a.get('offer_beacons', 0)) <= 0:
                messagebox.showinfo("Offer Beacon", "No Offer Beacons available.", parent=win)
                return
            # consume one beacon
            st = effects._state.setdefault('active', {})
            st['offer_beacons'] = max(0, int(st.get('offer_beacons', 0)) - 1)
            effects._save()
            # generate today's offers (one-shot)
            from database import generate_daily_contracts_if_needed
            generate_daily_contracts_if_needed()
            messagebox.showinfo("Offer Beacon", "Generated new offers. Check Available tab.", parent=win)
            refresh_views(); self.refresh_all()
        except Exception as e:
            messagebox.showwarning("Offer Beacon", f"Failed to use Offer Beacon: {e}", parent=win)

    RoundButton(hdr_frame, "Use Offer Beacon", fill=COLORS["PRIMARY"], fg=COLORS["WHITE"], padx=10, pady=6, radius=10, command=use_offer_beacon).pack(side="right")
    list_av = tk.Frame(tab_av, bg=COLORS["BG"]); list_av.pack(fill="both", expand=True, padx=8, pady=6)

    def clear_children(parent):
        for w in parent.winfo_children():
            w.destroy()

    def card(parent, title, subtitle, right_btn=None):
        c = tk.Frame(parent, bg=COLORS["CARD"], bd=0, highlightthickness=0)
        c.pack(fill="x", pady=6)
        left = tk.Frame(c, bg=COLORS["CARD"]); left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text=title, font=FONTS["h3"], bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(anchor="w", padx=12, pady=(10,0))
        tk.Label(left, text=subtitle, font=FONTS["small"], bg=COLORS["CARD"], fg=COLORS["MUTED"]).pack(anchor="w", padx=12, pady=(0,10))
        if right_btn:
            box = tk.Frame(c, bg=COLORS["CARD"]); box.pack(side="right", padx=12)
            right_btn(box)
        return c

    def refresh_my():
        clear_children(list_my)
        active = _safe_get_active_contracts(date.today().isoformat())
        if not active:
            tk.Label(list_my, text="No active contracts.", bg=COLORS["BG"], fg=COLORS["MUTED"]).pack(pady=8)
            return

        for cdata in active:
            title = cdata["title"]
            until = cdata.get("end_date")
            status = "BROKEN" if cdata.get("broken") else "ACTIVE"
            subtitle = f"Until {until}  •  Status: {status}  •  Penalty {cdata.get('penalty_xp',100)} XP"

            def make_btns(box, cid=cdata["id"]):
                def break_it():
                    _active = _safe_get_active_contracts(date.today().isoformat())
                    target = next((c for c in _active if c["id"] == cid), None)

                    if not target:
                        messagebox.showinfo("Contract", "This contract is already inactive or broken.", parent=win)
                        refresh_views()
                        return


                    pen = int(target.get("penalty_xp", 100))
                    already = int(target.get("penalty_applied", 0)) == 1

                    # mark broken
                    mark_contract_broken(cid)

                    if not already:
                        from exp_system import add_total_xp
                        from shop.effects import effects
                        # Use contract shield if available
                        if effects.consume_contract_shield():
                            pen = int(round(pen * 0.5))
                        add_total_xp(-abs(pen) * 10)  # same scale as entries (pts*10)
                        mark_contract_penalty_applied(cid)
                        try:
                            from sound import play_sfx
                            play_sfx("statsDown")
                        except Exception:
                            pass

                    messagebox.showinfo(
                        "Contract",
                        ("Penalty applied: -" + str(abs(pen)) + " XP." if not already else "Penalty already applied earlier."),
                        parent=win
                    )

                    refresh_views()
                    self.refresh_all()

                RoundButton(box, "Mark Broken",
                            fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
                            fg=COLORS["WHITE"], padx=14, pady=8, radius=12, command=break_it).pack(pady=10)

                # Use a Grace Period to extend this contract by one day
                def use_grace():
                    try:
                        from shop.effects import effects
                        if int(effects.dump().get('active', {}).get('grace_periods', 0)) <= 0:
                            messagebox.showinfo("Grace Period", "No Grace Periods available.", parent=win)
                            return
                        # extend end_date by +1 day
                        from database import get_connection
                        conn = get_connection(); cur = conn.cursor()
                        cur.execute("SELECT end_date FROM contracts WHERE id=?", (cid,))
                        row = cur.fetchone()
                        if not row:
                            messagebox.showinfo("Grace Period", "Contract not found.", parent=win)
                            conn.close(); return
                        ed = row[0]
                        from datetime import datetime, timedelta
                        try:
                            ed_dt = datetime.fromisoformat(ed)
                        except Exception:
                            # fallback to date only
                            ed_dt = datetime.fromisoformat(ed + 'T00:00:00')
                        new_ed = (ed_dt + timedelta(days=1)).date().isoformat()
                        cur.execute("UPDATE contracts SET end_date=? WHERE id=?", (new_ed, cid))
                        conn.commit(); conn.close()
                        # consume one grace period (decrement stored count)
                        st = effects._state.setdefault('active', {})
                        st['grace_periods'] = max(0, int(st.get('grace_periods', 0)) - 1)
                        effects._save()
                        messagebox.showinfo("Grace Period", "Contract extended by 1 day.", parent=win)
                    except Exception as e:
                        messagebox.showwarning("Grace Period", f"Failed to apply Grace Period: {e}", parent=win)
                    refresh_views(); self.refresh_all()

                RoundButton(box, "Use Grace", fill=COLORS["PRIMARY"], fg=COLORS["WHITE"], padx=8, pady=6, radius=8, command=use_grace).pack(pady=4)

            card(list_my, title, subtitle, right_btn=make_btns)

    def refresh_av():
        clear_children(list_av)
        offers = get_available_contracts()
        full = get_active_contracts_count() >= 3
        if not offers:
            tk.Label(list_av, text="No offers right now. Check again tomorrow!",
                     bg=COLORS["BG"], fg=COLORS["MUTED"]).pack(pady=8)
            return

        for o in offers:
            subtitle = f"Expires: {o['expires_at']}  •  Lasts: {o['duration_days']} day(s)  •  Penalty {o['penalty_xp']} XP"

            def make_btns(box, oid=o["id"]):
                def claim():
                    try:
                        claim_contract_offer(oid)
                    except ValueError as e:
                        messagebox.showwarning("Cannot claim", str(e), parent=win); return
                    refresh_views(); self.refresh_all()

                RoundButton(
                    box,
                    ("Full (3/3)" if full else "Claim"),
                    fill=(COLORS["MUTED"] if full else COLORS["PRIMARY"]),
                    hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                    fg=COLORS["WHITE"],
                    padx=14, pady=8, radius=12,
                    command=(None if full else claim),
                ).pack(pady=10)

            card(list_av, o["title"], subtitle, right_btn=make_btns)

    def refresh_views():
        try:
            if get_personal_active_count() >= 1 or get_active_contracts_count() >= 3:
                for child in form.winfo_children():
                    child.configure(state="disabled")
            else:
                for child in form.winfo_children():
                    child.configure(state="normal")
        except Exception:
            pass
        refresh_my(); refresh_av()

    refresh_views()
