# animations.py — robust helpers to animate IntVars / progress bars
import tkinter as tk

def _after_target(var, fallback=None):
    """
    Return something we can call .after(...) on.
    Handles Tk variants where IntVar has _root (attr) or _root() (method),
    or only _tk, or we fall back to the default root.
    """
    if fallback is not None:
        return fallback
    # 1) _root may be a Tk instance (attr)
    r = getattr(var, "_root", None)
    if r is not None:
        try:
            # if it's callable (older Tk), call it to get Tk
            return r() if callable(r) else r
        except Exception:
            pass
    # 2) Some builds expose _tk
    r = getattr(var, "_tk", None)
    if r is not None:
        return r
    # 3) Last resort: default root
    try:
        return tk._get_default_root()
    except Exception:
        return None

def animate_intvar(var: tk.IntVar, start: int, end: int,
                   duration_ms=350, steps=30, ease=True, widget=None):
    """Tween an IntVar from start to end with optional easing."""
    target = _after_target(var, fallback=widget)
    if target is None or start == end or steps <= 0 or duration_ms <= 0:
        var.set(end)
        return

    delta = end - start
    idx = {"i": 0}

    def step():
        i = idx["i"]
        t = (i + 1) / steps
        if ease:
            # smoothstep
            t = t * t * (3 - 2 * t)
        var.set(int(round(start + delta * t)))
        idx["i"] += 1
        if idx["i"] < steps:
            target.after(max(1, duration_ms // steps), step)
        else:
            var.set(end)

    var.set(start)
    step()

def flash_widget(widget, times=2, on="#FFFFFF", off=None, interval=120):
    """Quick flash to draw attention."""
    if off is None:
        off = widget.cget("bg")
    state = {"n": 0}

    def tick():
        if state["n"] >= times * 2:
            widget.config(bg=off)
            return
        widget.config(bg=on if state["n"] % 2 == 0 else off)
        state["n"] += 1
        widget.after(interval, tick)

    tick()
