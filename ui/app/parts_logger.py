# ui/app/parts_logger.py
# "Logger" — plan tomorrow's non-negotiables, check off today's, and apply reward/penalty

import tkinter as tk
from tkinter import messagebox
from datetime import date, timedelta

from constants import COLORS, FONTS
from widgets import RoundButton
from exp_system import add_total_xp, get_total_xp, level_from_xp
from shop.currency import add_coins, add_shards
from database import (
    add_nn_task, get_nn_tasks, set_nn_completed, delete_nn_task,
    nn_result_applied, set_nn_result_applied
)

# Tunables (XP is your global pool; this doesn't move a specific trait)
REWARD_PER_TASK  = 50    # if ALL tasks done → +N * REWARD_PER_TASK
PENALTY_PER_MISS = 40    # if ANY missing → -misses * PENALTY_PER_MISS  (strict non-negotiables)

def _human_summary(total: int, done: int, xp: int) -> str:
    if total == 0:
        return "No tasks planned."
    if done == total:
        return f"All {total}/{total} done → +{xp} XP"
    misses = total - done
    return f"{done}/{total} done, {misses} missed → {xp:+d} XP"

from shop.effects import effects

def _compute_xp(total: int, done: int) -> int:
    if total <= 0:
        return 0
    # Task Doubler: if available and at least one task done, count one completed task twice (one-time)
    try:
        td = int(effects.dump().get('active', {}).get('task_doubler', 0) or 0)
    except Exception:
        td = 0
    if td > 0 and done > 0:
        # apply one-time doubling: effectively +1 done (capped at total)
        done = min(total, done + 1)
        # consume one
        try:
            st = effects._state.setdefault('active', {})
            st['task_doubler'] = max(0, int(st.get('task_doubler', 0)) - 1)
            effects._save()
        except Exception:
            pass

    if done == total:
        # Apply logger full bonus if available
        base = total * REWARD_PER_TASK
        bonus_pct = effects.logger_full_bonus_pct()
        return int(round(base * (1 + bonus_pct)))
    # strict: any miss yields a penalty proportional to misses
    misses = total - done
    base_penalty = -misses * PENALTY_PER_MISS
    # Apply logger penalty buffer if available
    buffer_pct = effects.logger_penalty_buffer_pct()
    if buffer_pct > 0:
        base_penalty = int(round(base_penalty * (1 - buffer_pct)))
        # consume one-time buffer if flagged
        try:
            # only consume if explicitly one-time
            a = effects.dump().get('active', {})
            if a.get('logger_penalty_buffer_one_time'):
                effects.consume_logger_penalty_buffer()
        except Exception:
            pass
    return base_penalty

def open_logger(self):
    """Toplevel UI: Today (checklist + Apply) / Plan Tomorrow (add & manage)."""
    win = tk.Toplevel(self.root)
    win.title("Logger — Non-negotiables")
    win.configure(bg=COLORS["BG"])
    win.geometry("640x520")
    win.grab_set()

    # Dates
    today = date.today()
    tomorrow = today + timedelta(days=1)
    today_s = today.isoformat()
    tom_s   = tomorrow.isoformat()

    # ----- Header -----
    hdr = tk.Frame(win, bg=COLORS["BG"]); hdr.pack(fill="x", padx=12, pady=(12,6))
    tk.Label(hdr, text="Non-negotiables", font=FONTS["h2"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(side="left")
    # Ensure any planner-edge scheduled for 'tomorrow' is applied when opening the logger
    try:
        effects.shift_logger_next_to_active()
    except Exception:
        pass

    # Tabs
    nb = tk.Frame(win, bg=COLORS["BG"]); nb.pack(fill="both", expand=True, padx=12, pady=8)

    # -- LEFT: Today --
    left = tk.Frame(nb, bg=COLORS["BG"]); left.pack(side="left", fill="both", expand=True, padx=(0,6))
    tk.Label(left, text=f"Today ({today_s})", font=FONTS["h3"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(anchor="w", pady=(0,6))

    list_today = tk.Frame(left, bg=COLORS["CARD"]); list_today.pack(fill="both", expand=True)
    foot_today = tk.Frame(left, bg=COLORS["BG"]); foot_today.pack(fill="x", pady=(8,0))
    status_lbl = tk.Label(foot_today, text="", bg=COLORS["BG"], fg=COLORS["MUTED"])
    status_lbl.pack(side="left")

    def render_today():
        for w in list_today.winfo_children(): w.destroy()
        rows = get_nn_tasks(today_s)
        applied = nn_result_applied(today_s)

        if not rows:
            tk.Label(list_today, text="No tasks set for today.\nPlan some yesterday from the 'Plan Tomorrow' tab!",
                     bg=COLORS["CARD"], fg=COLORS["MUTED"], font=FONTS["small"]).pack(pady=14)
        else:
            for r in rows:
                row = tk.Frame(list_today, bg=COLORS["CARD"]); row.pack(fill="x", pady=2, padx=8)
                var = tk.IntVar(value=int(r["completed"]))
                def _mkcmd(task_id=r["id"], v=var):
                    return lambda: set_nn_completed(task_id, bool(v.get()))
                chk = tk.Checkbutton(row, variable=var, command=_mkcmd(),
                                     text=r["text"], onvalue=1, offvalue=0,
                                     bg=COLORS["CARD"], fg=COLORS["TEXT"], selectcolor=COLORS["CARD"],
                                     activebackground=COLORS["CARD"], anchor="w")
                chk.pack(side="left", fill="x", expand=True)

                # Disable ticking after result applied
                if applied:
                    chk.configure(state="disabled")

        # Footer controls
        for w in foot_today.winfo_children():
            if isinstance(w, RoundButton): w.destroy()

        total = len(get_nn_tasks(today_s))
        done  = sum(1 for r in get_nn_tasks(today_s) if r["completed"])
        xp = _compute_xp(total, done)

        status_lbl.config(text=_human_summary(total, done, xp))

        def do_apply():
            nonlocal xp, total, done
            if total <= 0:
                messagebox.showinfo("Logger", "No tasks planned for today.", parent=win); return
            if nn_result_applied(today_s):
                messagebox.showinfo("Logger", "Today's result already applied.", parent=win); return

            before_lvl = level_from_xp(get_total_xp())
            add_total_xp(xp)
            set_nn_result_applied(today_s, xp)
            # coin reward from logger completion: reward some coins (10% of XP)
            try:
                if xp > 0:
                    coins = max(1, int(round(xp * 0.10)))
                    try: add_coins(coins)
                    except Exception: pass
            except Exception:
                pass
            message = ("Perfect! +" + str(xp) + " XP 🎉") if done == total else ("Applied " + str(xp) + " XP")
            messagebox.showinfo("Logger", message, parent=win)
            render_today()
            try: self.refresh_all()
            except Exception: pass
            after_lvl = level_from_xp(get_total_xp())
            if after_lvl > before_lvl:
                try:
                    from sound import play_sfx
                    play_sfx("levelUp")
                except Exception:
                    pass

        RoundButton(foot_today, ("Applied" if nn_result_applied(today_s) else "Apply Result"),
                    fill=(COLORS["MUTED"] if nn_result_applied(today_s) else COLORS["PRIMARY"]),
                    hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                    fg=COLORS["WHITE"], padx=14, pady=8, radius=12,
                    command=(None if nn_result_applied(today_s) else do_apply)).pack(side="right")

    # -- RIGHT: Plan Tomorrow --
    right = tk.Frame(nb, bg=COLORS["BG"]); right.pack(side="left", fill="both", expand=True, padx=(6,0))
    tk.Label(right, text=f"Plan Tomorrow ({tom_s})", font=FONTS["h3"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(anchor="w", pady=(0,6))

    form = tk.Frame(right, bg=COLORS["CARD"]); form.pack(fill="x")
    tk.Label(form, text="Add task:", bg=COLORS["CARD"], fg=COLORS["TEXT"]).grid(row=0, column=0, padx=10, pady=8, sticky="w")
    entry_var = tk.StringVar()
    tk.Entry(form, textvariable=entry_var, width=32).grid(row=0, column=1, padx=(0,8), pady=8, sticky="w")

    def add_task():
        text = entry_var.get().strip()
        if not text: return
        add_nn_task(tom_s, text)
        entry_var.set("")
        render_tomorrow()

    RoundButton(form, "Add",
                fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS["WHITE"], padx=12, pady=8, radius=12,
                command=add_task).grid(row=0, column=2, padx=8, pady=8)

    list_tom = tk.Frame(right, bg=COLORS["CARD"]); list_tom.pack(fill="both", expand=True, pady=(8,0))

    def render_tomorrow():
        for w in list_tom.winfo_children(): w.destroy()
        rows = get_nn_tasks(tom_s)
        if not rows:
            tk.Label(list_tom, text="No tasks planned for tomorrow yet.", bg=COLORS["CARD"], fg=COLORS["MUTED"]).pack(pady=14)
            return
        for r in rows:
            row = tk.Frame(list_tom, bg=COLORS["CARD"]); row.pack(fill="x", pady=2, padx=8)
            tk.Label(row, text="• " + r["text"], bg=COLORS["CARD"], fg=COLORS["TEXT"]).pack(side="left", padx=2)
            def _del(task_id=r["id"]):
                delete_nn_task(task_id); render_tomorrow()
            RoundButton(row, "Delete",
                        fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
                        fg=COLORS["WHITE"], padx=10, pady=6, radius=10,
                        command=_del).pack(side="right")

    render_today()
    render_tomorrow()
