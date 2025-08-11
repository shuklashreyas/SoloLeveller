# widgets.py — rounded canvas button (no native focus ring)
import tkinter as tk
from constants import COLORS, FONTS

# Subtle shadow color (Tkinter can't do alpha like #00000024)
SHADOW = "#C7CAD1"   # light grey shadow

class RoundButton(tk.Canvas):
    def __init__(self, master, text, command=None,
                 fill=COLORS["PRIMARY"], fg=COLORS["WHITE"],
                 hover_fill=None, radius=14, padx=18, pady=8, **kwargs):
        super().__init__(master, highlightthickness=0, bd=0,
                         bg=master.cget("bg"), height=1, width=1, **kwargs)
        self.command = command
        self.fg = fg
        self.fill = fill
        self.hover_fill = hover_fill or fill
        self.radius = radius
        self.padx, self.pady = padx, pady

        self._rect = None
        self._text = None
        self._draw(text)
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda e: self._set_fill(self.hover_fill))
        self.bind("<Leave>", lambda e: self._set_fill(self.fill))

    def _draw(self, text):
        # measure text
        tmp = tk.Label(self, text=text, font=FONTS["btn"])
        tmp.update_idletasks()
        w = tmp.winfo_reqwidth()
        h = tmp.winfo_reqheight()
        tmp.destroy()

        width = w + self.padx * 2
        height = h + self.pady * 2
        r = self.radius
        self.config(width=width, height=height)
        self.delete("all")

        # drop shadow (no alpha in Tk, so use a light grey)
        self.create_round_rect(2, 3, width, height, r, fill=SHADOW, outline="")

        # main pill
        self._rect = self.create_round_rect(0, 0, width-2, height-2, r,
                                            fill=self.fill, outline="")

        self._text = self.create_text(width//2, height//2, text=text,
                                      fill=self.fg, font=FONTS["btn"])

    def create_round_rect(self, x1, y1, x2, y2, r, **kwargs):
        # rounded rectangle via rectangles + arcs
        body = self.create_rectangle(x1+r, y1, x2-r, y2, **kwargs)
        self.create_rectangle(x1, y1+r, x2, y2-r, **kwargs)
        # corners
        self.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90, style="pieslice", **kwargs)
        self.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90, style="pieslice", **kwargs)
        self.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90, style="pieslice", **kwargs)
        self.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90, style="pieslice", **kwargs)
        return body

    def _set_fill(self, color):
        self.itemconfig(self._rect, fill=color)

    def _click(self, _):
        if self.command:
            self.command()

    def enable(self, enabled=True):
        """Enable/disable look + click."""
        if enabled:
            self._set_fill(self.fill)
            self.itemconfig(self._text, fill=self.fg)
            self.bind("<Button-1>", self._click)
        else:
            self._set_fill("#C7CAD1")
            self.itemconfig(self._text, fill="#7B7F87")
            self.unbind("<Button-1>")
