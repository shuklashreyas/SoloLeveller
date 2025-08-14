import tkinter as tk
from tkinter import ttk
from constants import COLORS, PALETTES, set_theme, FONTS
from widgets import RoundButton
from database import set_meta, get_meta
from bgm import start_bgm_shuffle, stop_bgm
from sound import set_muted
from database import generate_daily_contracts_if_needed, get_available_offers_count


def ensure_offers_today(self, min_count: int = 3):
    try:
        if generate_daily_contracts_if_needed:
            generate_daily_contracts_if_needed()
        if get_available_offers_count() < min_count:
            set_meta("offers_day", "")
            if generate_daily_contracts_if_needed:
                generate_daily_contracts_if_needed()
    except Exception:
        pass


def toggle_sound(self):
    self.sound_enabled = not self.sound_enabled
    muted = (not self.sound_enabled)
    set_meta("sound_muted", "1" if muted else "0")
    try:
        set_muted(muted)
    except Exception:
        pass

    try:
        if muted:
            stop_bgm()
        else:
            start_bgm_shuffle(volume=0.22, crossfade_ms=700)
    except Exception:
        pass

    try:
        self.actions.set_sound_state(self.sound_enabled)
    except Exception:
        pass


def open_theme_picker(self):
    win = tk.Toplevel(self.root)
    win.title("Choose Theme")
    win.configure(bg=COLORS["BG"])
    win.geometry("360x210")
    win.grab_set()

    tk.Label(win, text="Theme", font=("Helvetica", 14, "bold"),
             bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(12, 6))

    names = list(PALETTES.keys())
    current = get_meta("theme") or names[0]
    var = tk.StringVar(value=current)

    cb = ttk.Combobox(win, values=names, textvariable=var, state="readonly", width=28)
    cb.pack(pady=8)

    def apply_and_close():
        name = var.get()
        if name not in PALETTES:
            return
        set_theme(name)
        set_meta("theme", name)
        rebuild_ui(self)
        win.destroy()

    RoundButton(win, "Apply Theme",
                fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS["WHITE"], padx=16, pady=8, radius=12,
                command=apply_and_close).pack(pady=14)


def rebuild_ui(self):
    # Destroy and rebuild with new theme colors
    for w in self.root.winfo_children():
        w.destroy()

    self.root.configure(bg=COLORS["BG"])

    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    from .parts_build import apply_styles, build_ui
    apply_styles(self, style)
    build_ui(self)
    self.refresh_all(first=False)


def on_close(self):
    try:
        stop_bgm()
    except Exception:
        pass
    finally:
        self.root.destroy()
