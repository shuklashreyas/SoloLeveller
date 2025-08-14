# ui/components/actions.py
import tkinter as tk
from constants import COLORS, FONTS
from widgets import RoundButton

class ActionsBar(tk.Frame):
    def __init__(
        self,
        master,
        on_atone,
        on_sin,
        on_theme,
        on_contracts=None,
        on_faq=None,
        on_sound_toggle=None,
        on_today=None,
        on_random_challenge=None,
    ):
        super().__init__(master, bg=COLORS["BG"])

        # Left cluster
        left = tk.Frame(self, bg=COLORS["BG"])
        left.pack(side="left")

        # Today jump
        if on_today:
            self.today_btn = RoundButton(
                left, "Today",
                fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS["TEXT"], padx=14, pady=10, radius=14,
                command=on_today
            )
            self.today_btn.pack(side="left", padx=(0, 10))

        # Atoning & Sin
        self.atone_btn = RoundButton(
            left, "Atone",
            fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["WHITE"], padx=18, pady=10, radius=16,
            command=on_atone
        ); self.atone_btn.pack(side="left", padx=10)

        self.sin_btn = RoundButton(
            left, "Sin",
            fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
            fg=COLORS["WHITE"], padx=18, pady=10, radius=16,
            command=on_sin
        ); self.sin_btn.pack(side="left", padx=10)

        # Random Challenge
        self.challenge_btn = None
        if on_random_challenge:
            self.challenge_btn = RoundButton(
                left, "Random Challenge",
                fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
                fg=COLORS["WHITE"], padx=20, pady=12, radius=18,
                command=on_random_challenge
            )
            self.challenge_btn.pack(side="left", padx=14)

        # Contracts (stands out a bit)
        self.contracts_btn = None
        if on_contracts:
            self.contracts_btn = RoundButton(
                left, "Contracts",
                fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
                fg=COLORS["WHITE"], padx=22, pady=12, radius=18,
                command=on_contracts
            ); self.contracts_btn.pack(side="left", padx=16)

        # Tiny badge next to Contracts for "offers"
        self._badge = tk.Label(self, text="", font=FONTS["small"], bg=COLORS["BG"], fg=COLORS["PRIMARY"])
        self._badge.pack(side="left")

        # Right cluster
        right = tk.Frame(self, bg=COLORS["BG"]); right.pack(side="right")

        # Theme
        self.theme_btn = RoundButton(
            right, "Theme",
            fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["TEXT"], padx=16, pady=10, radius=16,
            command=on_theme
        ); self.theme_btn.pack(side="left", padx=8)

        # FAQ (optional)
        if on_faq:
            self.faq_btn = RoundButton(
                right, "FAQ",
                fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS["TEXT"], padx=14, pady=10, radius=16,
                command=on_faq
            ); self.faq_btn.pack(side="left", padx=8)

        # Sound toggle (optional)
        self._sound_btn = None
        if on_sound_toggle:
            self._sound_btn = RoundButton(
                right, "Sound: On",
                fill=COLORS["CARD"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
                fg=COLORS["TEXT"], padx=14, pady=10, radius=16,
                command=on_sound_toggle
            ); self._sound_btn.pack(side="left", padx=8)

        # Spacer
        tk.Label(self, text="", bg=COLORS["BG"]).pack(side="right", expand=True)

    def enable(self, is_today: bool):
        """Enable/disable inputs that should be blocked for non-today views."""
        self.atone_btn.enable(is_today)
        self.sin_btn.enable(is_today)
        if self.challenge_btn:
            self.challenge_btn.enable(is_today)

    # Contracts badge "Contracts (n)" + dot text
    def set_contracts_badge(self, n: int):
        if not self.contracts_btn:
            return
        n = int(n)
        label = "Contracts" if n <= 0 else f"Contracts ({n})"
        self.contracts_btn.set_text(label)
        self._badge.config(text=("• New offers" if n > 0 else ""))

    # Reflect sound state on the button label
    def set_sound_state(self, enabled: bool):
        if self._sound_btn:
            self._sound_btn.set_text("Sound: On" if enabled else "Sound: Off")
