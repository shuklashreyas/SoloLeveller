from database import initialize_db
import tkinter as tk
from ui.app import HabitTrackerApp

if __name__ == "__main__":
    initialize_db()
    root = tk.Tk()
    HabitTrackerApp(root)
    root.mainloop()
