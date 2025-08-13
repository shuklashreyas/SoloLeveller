# ui/components/actions.py
import tkinter as tk
from constants import COLORS, FONTS
from widgets import RoundButton

class ActionsBar(tk.Frame):
    """
    Bottom action bar with Atone, Sin, Theme, Contracts, and FAQ buttons.
    Only Atone/Sin are disabled when viewing non-today dates.
    """
    def __init__(self, master, *, on_atone, on_sin, on_theme, on_contracts=None, on_faq=None):
        super().__init__(master, bg=COLORS["BG"])

        # Left cluster of primary actions
        left = tk.Frame(self, bg=COLORS["BG"])
        left.pack(side="left")

        # Atone
        self.atone_btn = RoundButton(
            left, "Atone",
            fill=COLORS["PRIMARY"], hover_fill=COLORS.get("PRIMARY_HOVER", COLORS["PRIMARY"]),
            fg=COLORS["WHITE"], padx=18, pady=10, radius=16,
            command=on_atone
        )
        self.atone_btn.pack(side="left", padx=8)

        # Sin
        self.sin_btn = RoundButton(
            left, "Sin",
            fill=COLORS["ACCENT"], hover_fill=COLORS.get("ACCENT_HOVER", COLORS["ACCENT"]),
            fg=COLORS["WHITE"], padx=18, pady=10, radius=16,
            command=on_sin
        )
        self.sin_btn.pack(side="left", padx=8)

        # Theme
        self.theme_btn = RoundButton(
            left, "Theme",
            fill=COLORS["CARD"], hover_fill=COLORS.get("ACCENT_HOVER", "#E3D4FF"),
            fg=COLORS["TEXT"], padx=16, pady=10, radius=14,
            command=on_theme
        )
        self.theme_btn.pack(side="left", padx=8)

        # Contracts (optional)
        self.contracts_btn = None
        if on_contracts is not None:
            self.contracts_btn = RoundButton(
                left, "Contracts",
                fill=COLORS["CARD"], hover_fill=COLORS.get("ACCENT_HOVER", "#E3D4FF"),
                fg=COLORS["TEXT"], padx=16, pady=10, radius=14,
                command=on_contracts
            )
            self.contracts_btn.pack(side="left", padx=8)

        # FAQ (optional)
        self.faq_btn = None
        if on_faq is not None:
            self.faq_btn = RoundButton(
                left, "FAQ",
                fill=COLORS["CARD"], hover_fill=COLORS.get("ACCENT_HOVER", "#E3D4FF"),
                fg=COLORS["TEXT"], padx=16, pady=10, radius=14,
                command=on_faq
            )
            self.faq_btn.pack(side="left", padx=8)

        # Right-side note
        self.note = tk.Label(
            self, text="You can log only for TODAY.",
            font=FONTS["small"], bg=COLORS["BG"], fg=COLORS["TEXT"]
        )
        self.note.pack(side="right", padx=16)

    def enable(self, is_today: bool):
        """Enable/disable only Atone & Sin; others remain usable."""
        self.atone_btn.enable(is_today)
        self.sin_btn.enable(is_today)
        # Theme/Contracts/FAQ always enabled; update note visibility
        self.note.config(text=("You can log only for TODAY." if not is_today else ""))
