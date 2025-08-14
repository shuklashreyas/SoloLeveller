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
    tk.Label(tab_av, text="Time-limited offers (claim before they expire)",
             font=FONTS["h2"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(anchor="w", padx=8, pady=(8, 2))
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
