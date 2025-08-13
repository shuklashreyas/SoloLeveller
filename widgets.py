# widgets.py
import tkinter as tk
import tkinter.font as tkfont
from sound import play_sfx

class RoundButton(tk.Frame):
    def __init__(self, master, text, command=None,
                 fill="#6C63FF", hover_fill="#7A71FF",
                 fg="#FFFFFF", padx=14, pady=8, radius=12,
                 font=("Helvetica", 12, "bold")):
        super().__init__(master, bg=getattr(master, "bg", master["bg"]))
        self.text, self.command = text, command
        self.fill, self.hover_fill, self.fg = fill, hover_fill, fg
        self.padx, self.pady, self.radius, self.font = padx, pady, radius, font

        parent_bg = getattr(master, "bg", master["bg"])
        self.canvas = tk.Canvas(self, bg=parent_bg, highlightthickness=0, bd=0)  # no borders
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Enter>", lambda e: self._set_hover(True))
        self.canvas.bind("<Leave>", lambda e: self._set_hover(False))
        self.canvas.bind("<Button-1>", lambda e: self._invoke())

        self._hovered = False
        self._enabled = True
        self._bg_id = self._text_id = None
        self.after(0, self._redraw)

    def enable(self, yes=True):
        self._enabled = bool(yes)
        self.canvas.itemconfigure(self._text_id, state=("normal" if yes else "disabled"))
        self.canvas.configure(cursor=("hand2" if yes else "arrow"))
        # dim the button when disabled
        if self._bg_id:
            self.canvas.itemconfigure(self._bg_id, stipple=("gray50" if not yes else ""))

    # ---- drawing ----
    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        pts = [
            x1+r, y1,  x2-r, y1,  x2, y1,  x2, y1+r,
            x2, y2-r,  x2, y2,  x2-r, y2,  x1+r, y2,
            x1, y2,    x1, y2-r, x1, y1+r, x1, y1
        ]
        return self.canvas.create_polygon(pts, smooth=True, splinesteps=36,
                                          outline="", width=0, **kwargs)

    def _redraw(self):
        self.canvas.delete("all")
        f = tkfont.Font(font=self.font)
        tw, th = f.measure(self.text), f.metrics("linespace")
        w, h = tw + self.padx*2, th + self.pady*2
        self.canvas.config(width=w, height=h)
        fill = self.hover_fill if self._hovered else self.fill
        self._bg_id = self._rounded_rect(0, 0, w, h, self.radius, fill=fill)
        self._text_id = self.canvas.create_text(w/2, h/2, text=self.text, fill=self.fg, font=self.font)

    def _set_hover(self, on):
        self._hovered = bool(on)
        self._redraw()

    def _invoke(self):
        if self._enabled and callable(self.command):
            play_sfx("click")   # NEW
            self.command()

