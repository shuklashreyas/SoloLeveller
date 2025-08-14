import tkinter as tk
from tkinter import ttk
from constants import COLORS, PALETTES, set_theme, FONTS
from database import get_meta
from sound import init as init_sound, set_muted
from bgm import init_bgm, start_bgm_shuffle, stop_bgm

from ..components.topbar import TopBar
from ..components.xp_strip import XPStrip
from ..components.stats import StatsPanel
from ..components.journal import JournalPanel
from ..components.logs import LogsPanel
from ..components.dailydouble import DailyDoublePanel
from ..components.actions import ActionsBar


def apply_styles(self, style: ttk.Style):
    style.configure("Treeview",
                    background=COLORS["CARD"],
                    fieldbackground=COLORS["CARD"],
                    foreground=COLORS["TEXT"],
                    rowheight=24)
    style.configure("Treeview.Heading",
                    background=COLORS["PRIMARY"],
                    foreground=COLORS["WHITE"])
    style.configure("XP.Horizontal.TProgressbar",
                    troughcolor=COLORS["CARD"],
                    background=COLORS["PRIMARY"])
    style.configure("Stat.Horizontal.TProgressbar",
                    troughcolor=COLORS.get("TRACK", "#D4D4D8"),
                    background=COLORS["ACCENT"])


def build_ui(self):
    # Init audio backends once
    init_sound()
    init_bgm()

    # Theme before widget creation
    saved_theme = get_meta("theme")
    if saved_theme and saved_theme in PALETTES:
        set_theme(saved_theme)

    # Mute state (default ON = not muted)
    muted_flag = (get_meta("sound_muted") == "1")
    self.sound_enabled = not muted_flag
    set_muted(muted_flag)

    # Window geometry and bg
    self.root.geometry("1544x890+5+43")
    self.root.configure(bg=COLORS["BG"])

    # Header
    self.topbar = TopBar(master=self.root,
                         on_prev=lambda: self.go_prev_day(),
                         on_next=lambda: self.go_next_day())
    self.topbar.pack(fill="x", pady=(12, 6))

    self.xpstrip = XPStrip(self.root)
    self.xpstrip.pack(fill="x", pady=(0, 10))

    # Main grid
    grid = tk.Frame(self.root, bg=COLORS["BG"])
    grid.pack(fill="both", expand=True, padx=12, pady=8)

    # Left
    left = tk.Frame(grid, bg=COLORS["BG"])
    left.pack(side="left", fill="both", expand=True, padx=(0, 8))

    self.stats = StatsPanel(left)
    self.stats.pack(side="top", fill="x", padx=4, pady=(0, 8))

    self.journal = JournalPanel(left, on_save=lambda txt: self.save_journal(txt))
    self.journal.pack(side="top", fill="both", expand=True, padx=4, pady=(0, 4))

    self.dd_panel = DailyDoublePanel(left)
    self.dd_panel.pack(side="top", fill="x", padx=4, pady=(0, 8))

    # Right
    right = tk.Frame(grid, bg=COLORS["BG"])
    right.pack(side="left", fill="both", expand=True, padx=(8, 0))

    self.logs = LogsPanel(right)
    self.logs.pack(fill="both", expand=True, padx=4, pady=0)

    # Actions (with optional sound toggle)
    try:
        self.actions = ActionsBar(
            self.root,
            on_atone=lambda: self.open_atone_dialog(),
            on_sin=lambda: self.open_sin_dialog(),
            on_theme=lambda: self.open_theme_picker(),
            on_contracts=lambda: self.open_contracts(),
            on_faq=None,
            on_sound_toggle=lambda: self.toggle_sound(),
        )
    except TypeError:
        self.actions = ActionsBar(
            self.root,
            on_atone=lambda: self.open_atone_dialog(),
            on_sin=lambda: self.open_sin_dialog(),
            on_theme=lambda: self.open_theme_picker(),
            on_contracts=lambda: self.open_contracts(),
        )
    self.actions.pack(fill="x", pady=10)

    # Start BGM if not muted
    if self.sound_enabled:
        try:
            start_bgm_shuffle(volume=0.22, crossfade_ms=700)
        except Exception:
            pass
