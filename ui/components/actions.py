# ui/components/actions.py
import tkinter as tk
from constants import COLORS, FONTS
from widgets import RoundButton

class ActionsBar(tk.Frame):
    def __init__(self, master, on_atone, on_sin, on_theme, on_contracts, on_faq=None, on_sound_toggle=None):
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

        # Make Contracts pop (accent color + subtle larger padding)
        self.contracts_btn = RoundButton(
            self, "Contracts",
            fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
            fg=COLORS["WHITE"], padx=22, pady=12, radius=18,
            command=on_contracts
        ); self.contracts_btn.pack(side="left", padx=16)

        # Tiny badge label (hidden when 0)
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

        # Flexible spacer pushes the sound toggle to the far right
        tk.Frame(self, bg=COLORS["BG"]).pack(side="left", expand=True, fill="x")

        # --- Sound toggle (right-aligned) ---
        self._on_sound_toggle = on_sound_toggle
        self.sound_btn = RoundButton(
            self, "🔊 Sound On",
            fill=COLORS["CARD"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
            fg=COLORS["TEXT"], padx=16, pady=10, radius=16,
            command=(lambda: self._on_sound_toggle() if self._on_sound_toggle else None)
        ); self.sound_btn.pack(side="right", padx=10)

    def enable(self, is_today: bool):
        self.atone_btn.enable(is_today)
        self.sin_btn.enable(is_today)

    # show "Contracts (n)" and a little badge if there are fresh offers
    def set_contracts_badge(self, n: int):
        n = int(n)
        label = "Contracts" if n <= 0 else f"Contracts ({n})"
        self.contracts_btn.set_text(label)
        self._badge.config(text=("• New offers" if n > 0 else ""))

    # update sound button label from app
    def set_sound_state(self, enabled: bool):
        self.sound_btn.set_text("🔊 Sound On" if enabled else "🔇 Muted")
