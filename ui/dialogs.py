import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from constants import COLORS, FONTS
from widgets import RoundButton


def ask_action(root, title, categories, menu_map):
    """
    Opens a modal dialog to pick (category, item) and returns:
        (category, item_text, points)  or  None if cancelled.
    """
    dlg = tk.Toplevel(root)
    dlg.title(title)
    dlg.geometry("560x380")
    dlg.configure(bg=COLORS["BG"])
    dlg.grab_set()

    tk.Label(dlg, text=("Choose a positive attribute" if title=="Atone" else "Choose a sin"),
             font=FONTS["h3"], bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(12, 6))

    cat_var = tk.StringVar(value=categories[0])
    cat_combo = ttk.Combobox(dlg, values=categories, textvariable=cat_var, state="readonly")
    cat_combo.pack(pady=4)

    tk.Label(dlg, text="Pick an item", bg=COLORS["BG"], fg=COLORS["TEXT"]).pack(pady=(10, 2))
    act_var = tk.StringVar()
    act_combo = ttk.Combobox(dlg, values=[], textvariable=act_var, state="readonly", width=46)
    act_combo.pack(pady=4)

    other_text = tk.Text(dlg, height=3, width=52, bg=COLORS["CARD"], fg=COLORS["TEXT"],
                         highlightthickness=0, relief="flat", font=FONTS["body"])
    other_text.pack(pady=6); other_text.pack_forget()

    info_lbl = tk.Label(dlg, text="", bg=COLORS["BG"], fg=COLORS["TEXT"])
    info_lbl.pack()

    def load_items(*_):
        items = [name for (name, _) in menu_map.get(cat_var.get(), [])]
        act_combo.config(values=items)
        if items: act_combo.current(0); update_info()

    def update_info(*_):
        other_text.pack_forget()
        sel, pts = act_var.get(), 0
        for (name, p) in menu_map.get(cat_var.get(), []):
            if name == sel: pts = p; break
        if sel == "Other…":
            info_lbl.config(text="Choose intensity (1–3).")
            other_text.pack(pady=6)
        else:
            info_lbl.config(text=f"Default points: {pts:+d}")

    cat_combo.bind("<<ComboboxSelected>>", load_items)
    act_combo.bind("<<ComboboxSelected>>", update_info)
    load_items()

    def on_save():
        cat, act = cat_var.get(), act_var.get()
        if not cat or not act:
            messagebox.showwarning("Missing", "Please choose a category and an item.", parent=dlg); return
        pts = None
        for (name, p) in menu_map.get(cat, []):
            if name == act: pts = p; break
        if act == "Other…":
            custom = other_text.get("1.0", "end").strip()
            if not custom:
                messagebox.showwarning("Missing", "Describe what you did.", parent=dlg); return
            intensity = simpledialog.askinteger("Intensity", "Pick 1 (light) to 3 (major).",
                                                minvalue=1, maxvalue=3, parent=dlg)
            if intensity is None: return
            # Sign of points (positive for Atone, negative for Sin) is handled by caller via menu_map
            pts = intensity if title == "Atone" else -intensity
            result[:] = [cat, custom, pts]
        else:
            result[:] = [cat, act, pts if pts is not None else (1 if title=="Atone" else -1)]
        dlg.destroy()

    result = [None]  # mutable holder
    RoundButton(
    dlg, "Save",
    command=on_save,
    fill=(COLORS["PRIMARY"] if title == "Atone" else COLORS["ACCENT"]),
    hover_fill=("#7A71FF" if title == "Atone" else "#19B8C7"),
    fg=COLORS["WHITE"],
    padx=14, pady=8, radius=12
).pack(pady=12)


    root.wait_window(dlg)
    return tuple(result) if result[0] else None
