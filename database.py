
# database.py — SQLite helpers for Habit Tracker
import sqlite3
from pathlib import Path

DB_FILE = Path("habit_tracker.db")

def get_connection():
    return sqlite3.connect(DB_FILE)

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attributes (
            name TEXT PRIMARY KEY,
            baseline INTEGER NOT NULL,
            score INTEGER NOT NULL
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            entry_type TEXT NOT NULL,
            category TEXT NOT NULL,
            item TEXT NOT NULL,
            points INTEGER NOT NULL,
            ts TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    conn.commit()
    conn.close()

def get_meta(key: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM meta WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_meta(key: str, value: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    conn.close()

def get_attributes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, baseline, score FROM attributes")
    rows = cur.fetchall()
    conn.close()
    out = {}
    for name, base, score in rows:
        out[name] = {"baseline": int(base), "score": int(score)}
    return out

def upsert_attribute(name: str, baseline: int, score: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO attributes(name, baseline, score) VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET baseline=excluded.baseline, score=excluded.score
    """, (name, int(baseline), int(score)))
    conn.commit()
    conn.close()

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def update_attribute_score(name: str, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT score FROM attributes WHERE name = ?", (name,))
    row = cur.fetchone()
    if not row:
        base = 50
        cur.execute("INSERT INTO attributes(name, baseline, score) VALUES (?, ?, ?)", (name, base, base))
        score = base
    else:
        score = int(row[0])
    new_score = clamp(score + int(delta), 35, 99)
    cur.execute("UPDATE attributes SET score = ? WHERE name = ?", (new_score, name))
    conn.commit()
    conn.close()

def insert_entry(date: str, entry_type: str, category: str, item: str, points: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO entries(date, entry_type, category, item, points) VALUES (?, ?, ?, ?, ?)
    """, (date, entry_type, category, item, int(points)))
    conn.commit()
    conn.close()

def get_entries_by_date(date: str):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT id, date, entry_type, category, item, points, ts FROM entries WHERE date = ? ORDER BY ts ASC", (date,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
