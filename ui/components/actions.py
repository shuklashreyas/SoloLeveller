# ui/components/actions.py
import tkinter as tk
from constants import COLORS, FONTS
from widgets import RoundButton

class ActionsBar(tk.Frame):
    def __init__(self, master, on_atone, on_sin, on_theme, on_contracts,
                 on_faq=None, on_sound_toggle=None, on_logger=None):
        super().__init__(master, bg=COLORS["BG"])

        self.atone_btn = RoundButton(
            self, "Atone",
            fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["WHITE"], padx=18, pady=10, radius=16,
            command=on_atone
        ); self.atone_btn.pack(side="left", padx=10)

        self.sin_btn = RoundButton(
            self, "Sin",
            fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
            fg=COLORS["WHITE"], padx=18, pady=10, radius=16,
            command=on_sin
        ); self.sin_btn.pack(side="left", padx=10)

        # Logger (non-negotiables)
        if on_logger:
            self.logger_btn = RoundButton(
                self, "Logger",
                fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS["WHITE"], padx=20, pady=12, radius=18,
                command=on_logger
            ); self.logger_btn.pack(side="left", padx=14)
        else:
            self.logger_btn = None

        # Contracts pops visually
        self.contracts_btn = RoundButton(
            self, "Contracts",
            fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
            fg=COLORS["WHITE"], padx=22, pady=12, radius=18,
            command=on_contracts
        ); self.contracts_btn.pack(side="left", padx=16)

        # Tiny badge near Contracts (hidden when 0)
        self._badge = tk.Label(self, text="", font=FONTS["small"],
                               bg=COLORS["BG"], fg=COLORS["PRIMARY"])
        self._badge.pack(side="left")

        self.theme_btn = RoundButton(
            self, "Theme",
            fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["TEXT"], padx=16, pady=10, radius=16,
            command=on_theme
        ); self.theme_btn.pack(side="left", padx=10)

        if on_faq:
            self.faq_btn = RoundButton(
                self, "FAQ",
                fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS["TEXT"], padx=14, pady=10, radius=16,
                command=on_faq
            ); self.faq_btn.pack(side="left", padx=10)

        # Right-aligned controls
        spacer = tk.Label(self, text="", bg=COLORS["BG"]); spacer.pack(side="right", expand=True)

        # Optional sound toggle
        self._sound_state = True
        if on_sound_toggle:
            self.sound_btn = RoundButton(
                self, "Sound: ON",
                fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS["TEXT"], padx=14, pady=10, radius=14,
                command=on_sound_toggle
            ); self.sound_btn.pack(side="right", padx=8)
        else:
            self.sound_btn = None

    def enable(self, is_today: bool):
        self.atone_btn.enable(is_today)
        self.sin_btn.enable(is_today)
        # Logger can be used any time (planning for tomorrow & checking today)

    # Contracts badge text like: Contracts (n) + a small dot hint
    def set_contracts_badge(self, n: int):
        n = int(n)
        label = "Contracts" if n <= 0 else f"Contracts ({n})"
        self.contracts_btn.set_text(label)
        self._badge.config(text=("• New offers" if n > 0 else ""))

    # Reflect mute state
    def set_sound_state(self, enabled: bool):
        self._sound_state = bool(enabled)
        if self.sound_btn:
            self.sound_btn.set_text("Sound: ON" if enabled else "Sound: OFF")
