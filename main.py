# main.py
import tkinter as tk
from database import initialize_db
from ui import HabitTrackerApp

def main():
    initialize_db()
    root = tk.Tk()
    HabitTrackerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
