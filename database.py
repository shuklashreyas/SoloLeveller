# database.py — SQLite helpers (attributes, entries, meta, journal, daily double, contracts)
import sqlite3
import random
from pathlib import Path
from datetime import date, timedelta, datetime

DB_FILE = Path("habit_tracker.db")

def get_connection():
    """Create a new connection per call; callers must close (or use context mgr)."""
    return sqlite3.connect(DB_FILE)

def initialize_db():
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nonnegotiables (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          date_for   TEXT NOT NULL,                         -- YYYY-MM-DD the tasks are for
          text       TEXT NOT NULL,
          completed  INTEGER NOT NULL DEFAULT 0,            -- 0/1
          created_ts TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
    """)


    # Core tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attributes(
            name TEXT PRIMARY KEY,
            baseline INTEGER NOT NULL,
            score INTEGER NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,        -- YYYY-MM-DD
            entry_type TEXT NOT NULL,  -- ATONE | SIN
            category TEXT NOT NULL,
            item TEXT NOT NULL,
            points INTEGER NOT NULL,
            ts TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS meta(
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS journal(
            date TEXT PRIMARY KEY,
            content TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_double (
          day TEXT PRIMARY KEY,           -- YYYY-MM-DD
          atone_category TEXT NOT NULL,
          sin_category   TEXT NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          title TEXT NOT NULL,
          start_date TEXT NOT NULL,       -- YYYY-MM-DD
          end_date   TEXT NOT NULL,       -- YYYY-MM-DD (inclusive)
          penalty_xp INTEGER NOT NULL DEFAULT 100,
          active INTEGER NOT NULL DEFAULT 1,
          broken INTEGER NOT NULL DEFAULT 0,
          penalty_applied INTEGER NOT NULL DEFAULT 0
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contract_offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        expires_at TEXT NOT NULL,       -- ISO datetime (localtime)
        duration_days INTEGER NOT NULL DEFAULT 1,
        penalty_xp INTEGER NOT NULL DEFAULT 100,
        claimed INTEGER NOT NULL DEFAULT 0
        );
    """)
    
    # Add is_personal flag if it doesn't exist yet
    try:
        cur.execute("ALTER TABLE contracts ADD COLUMN is_personal INTEGER NOT NULL DEFAULT 0;")
    except sqlite3.OperationalError:
        pass  # column already exists




    # Lightweight migration: add expires_at for hour-limited pacts if missing
    try:
        cur.execute("ALTER TABLE contracts ADD COLUMN expires_at TEXT")  # 'YYYY-MM-DD HH:MM:SS' localtime
    except sqlite3.OperationalError:
        pass  # already exists

    # Helpful indexes
    cur.execute("CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_contracts_active ON contracts(active)")

    conn.commit()
    conn.close()

# -------- meta --------
def get_meta(key: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM meta WHERE key=?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def set_meta(key: str, value: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO meta(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()

# -------- attributes --------
def get_attributes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, baseline, score FROM attributes")
    rows = cur.fetchall()
    conn.close()
    return {name: {"baseline": int(b), "score": int(s)} for name, b, s in rows}

def upsert_attribute(name: str, baseline: int, score: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO attributes(name, baseline, score) VALUES (?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET baseline=excluded.baseline, score=excluded.score
    """, (name, int(baseline), int(score)))
    conn.commit()
    conn.close()

def _clamp(x, lo, hi):
    return max(lo, min(hi, x))

def update_attribute_score(name: str, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT score FROM attributes WHERE name=?", (name,))
    row = cur.fetchone()
    if not row:
        base = 50
        cur.execute("INSERT INTO attributes(name, baseline, score) VALUES(?,?,?)", (name, base, base))
        score = base
    else:
        score = int(row[0])
    new_score = _clamp(score + int(delta), 35, 99)
    cur.execute("UPDATE attributes SET score=? WHERE name=?", (new_score, name))
    conn.commit()
    conn.close()

# -------- entries --------
def insert_entry(date: str, entry_type: str, category: str, item: str, points: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO entries(date, entry_type, category, item, points) VALUES(?,?,?,?,?)
    """, (date, entry_type, category, item, int(points)))
    conn.commit()
    conn.close()

def get_entries_by_date(date: str):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id, date, entry_type, category, item, points, ts
        FROM entries WHERE date=? ORDER BY ts ASC
    """, (date,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

# -------- journal --------
def get_journal(date: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT content FROM journal WHERE date=?", (date,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else ""

def upsert_journal(date: str, content: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO journal(date, content) VALUES(?, ?)
        ON CONFLICT(date) DO UPDATE SET content=excluded.content
    """, (date, content))
    conn.commit()
    conn.close()

# -------- daily double --------
def get_daily_double(day_iso: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT atone_category, sin_category FROM daily_double WHERE day=?", (day_iso,))
    row = cur.fetchone()
    conn.close()
    return {"atone": row[0], "sin": row[1]} if row else None

def set_daily_double(day_iso: str, atone_category: str, sin_category: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO daily_double(day, atone_category, sin_category) VALUES (?,?,?)",
        (day_iso, atone_category, sin_category)
    )
    conn.commit()
    conn.close()

def get_active_contracts(day_iso: str):
    deactivate_expired_and_broken()
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT id,title,start_date,end_date,penalty_xp,active,broken,penalty_applied,expires_at,is_personal
        FROM contracts
        WHERE active=1 AND broken=0 AND (
            (expires_at IS NULL AND date(?) BETWEEN date(start_date) AND date(end_date))
            OR (expires_at IS NOT NULL AND datetime('now','localtime') <= datetime(expires_at))
        )
        ORDER BY COALESCE(expires_at, end_date) ASC, id ASC
    """, (day_iso,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def create_contract(title: str, penalty_xp: int, start_iso: str, end_iso: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO contracts(title,start_date,end_date,penalty_xp,active,broken,penalty_applied,expires_at)
        VALUES (?,?,?,?,1,0,0,NULL)
    """, (title, start_iso, end_iso, int(penalty_xp)))
    conn.commit()
    conn.close()

def _insert_contract(title: str, penalty_xp: int, start_iso: str, end_iso: str = None, expires_at: str = None):
    """Internal helper for daily auto-generation (supports hour-limited contracts)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO contracts(title,start_date,end_date,penalty_xp,active,broken,penalty_applied,expires_at)
        VALUES (?,?,?,?,1,0,0,?)
    """, (title, start_iso, end_iso or start_iso, int(penalty_xp), expires_at))
    conn.commit()
    conn.close()

def mark_contract_broken(cid: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE contracts SET broken=1 WHERE id=?", (cid,))
    conn.commit()
    conn.close()

def mark_contract_penalty_applied(cid: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE contracts SET penalty_applied=1 WHERE id=?", (cid,))
    conn.commit()
    conn.close()
    
# --- add near the other "entries" helpers ---
def get_logged_days_in_range(start_iso: str, end_iso: str) -> set[str]:
    """
    Return a set of YYYY-MM-DD strings that have *any* logged content.
    Currently: entries table only (ATONE/SIN). If you also want days with
    Journal content to count as "available", uncomment the UNION below.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT date FROM entries
        WHERE date BETWEEN ? AND ?
        ORDER BY date ASC
    """, (start_iso, end_iso))
    rows = {r[0] for r in cur.fetchall()}

    # If you want journal-only days to be pickable too, uncomment:
    # cur.execute("""
    #     SELECT DISTINCT date FROM journal
    #     WHERE date BETWEEN ? AND ? AND TRIM(IFNULL(content,'')) <> ''
    # """, (start_iso, end_iso))
    # rows |= {r[0] for r in cur.fetchall()}

    conn.close()
    return rows


def deactivate_expired_and_broken():
    """
    Marks contracts inactive when they shouldn't count anymore:
      - broken=1
      - expired by hours (expires_at < now)
      - past end_date (for day-based)
    Returns total rows updated.
    """
    conn = get_connection()
    cur = conn.cursor()
    total = 0
    # Broken → inactive
    cur.execute("UPDATE contracts SET active=0 WHERE broken=1 AND active=1")
    total += cur.rowcount
    # Hour-limited expired → inactive
    cur.execute("""
        UPDATE contracts
        SET active=0
        WHERE active=1
          AND expires_at IS NOT NULL
          AND datetime(expires_at) < datetime('now','localtime')
    """)
    total += cur.rowcount
    # Day-based past end → inactive
    cur.execute("""
        UPDATE contracts
        SET active=0
        WHERE active=1
          AND expires_at IS NULL
          AND date('now','localtime') > date(end_date)
    """)
    total += cur.rowcount
    conn.commit()
    conn.close()
    return total


def generate_daily_contracts_if_needed():
    """
    Create 1–3 time-sensitive contracts once per calendar day.
    Some expire in hours (expires_at), others in days (end_date).
    Uses meta key 'contracts_generated_for' to ensure idempotence.
    """
    today = date.today().isoformat()
    if get_meta("contracts_generated_for") == today:
        return

    now = datetime.now()
    # pools: (title, penalty_xp, span)
    hourly_pool = [
        ("1-hour Journal + Meditate", 250, 2),   # 2 hours from now
        ("No phone for 2 hours", 200, 2),
        ("Deep Work 90 minutes", 220, 2),
    ]
    daily_pool = [
        ("No Social Media (today)", 300, 1),
        ("Walk 7k steps today", 180, 1),
        ("Lights out by 11pm", 200, 1),
    ]
    multi_day_pool = [
        ("Wake up by 7:00 AM (3 days)", 400, 3),
        ("No Social Media (7 days)", 800, 7),
    ]

    count = random.randint(1, 3)
    choices = []
    pools = [hourly_pool, daily_pool, multi_day_pool]
    random.shuffle(pools)
    for pool in pools:
        if pool and len(choices) < count:
            choices.append(random.choice(pool))
    while len(choices) < count:
        choices.append(random.choice(daily_pool + multi_day_pool + hourly_pool))

    for title, penalty, span in choices:
        # heuristic: if explicitly hourly in title or span small, make it hour-limited
        if "hour" in title.lower() or (span <= 3 and random.random() < 0.5):
            expires = (now + timedelta(hours=span)).strftime("%Y-%m-%d %H:%M:%S")
            _insert_contract(title, penalty_xp=penalty, start_iso=today, end_iso=today, expires_at=expires)
        else:
            end = (date.today() + timedelta(days=span - 1)).isoformat()
            _insert_contract(title, penalty_xp=penalty, start_iso=today, end_iso=end, expires_at=None)

    set_meta("contracts_generated_for", today)

# -------- baselines --------
def get_baselines():
    """Return {trait: baseline_int}. Uses attributes.baseline if present, else meta 'baseline:<Trait>'."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("PRAGMA table_info(attributes)")
        cols = cur.fetchall()
        has_baseline = any(c[1] == "baseline" for c in cols)
    except Exception:
        has_baseline = False

    out = {}
    if has_baseline:
        cur.execute("SELECT name, baseline FROM attributes")
        for name, base in cur.fetchall():
            out[name] = int(base)
    else:
        cur.execute("SELECT key, value FROM meta WHERE key LIKE 'baseline:%'")
        for k, v in cur.fetchall():
            out[k.split("baseline:", 1)[1]] = int(v)
    conn.close()
    return out

from datetime import datetime, timedelta as _td

# ---- counts & filters ----
def get_active_contracts_count() -> int:
    deactivate_expired_and_broken()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*)
        FROM contracts
        WHERE active=1 AND broken=0 AND (
            (expires_at IS NULL AND date('now','localtime') BETWEEN date(start_date) AND date(end_date))
            OR (expires_at IS NOT NULL AND datetime('now','localtime') <= datetime(expires_at))
        )
    """)
    n = int(cur.fetchone()[0])
    conn.close()
    return n


def get_personal_active_count() -> int:
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM contracts
        WHERE active=1 AND broken=0 AND is_personal=1 AND (
            (expires_at IS NULL AND date('now','localtime') BETWEEN date(start_date) AND date(end_date))
            OR (expires_at IS NOT NULL AND datetime('now','localtime') <= datetime(expires_at))
        )
    """)
    n = int(cur.fetchone()[0]); conn.close(); return n

# ---- personal contract creation with limits ----
def create_personal_contract_limited(title: str, days: int, penalty_xp: int = 200):
    deactivate_expired_and_broken()
    days = max(1, min(7, int(days)))  # 1..7
    if get_personal_active_count() >= 1:
        raise ValueError("You already have an active personal contract.")
    if get_active_contracts_count() >= 3:
        raise ValueError("You already have 3 active contracts.")

    today = date.today()
    start_iso = today.isoformat()
    end_iso = (today + _td(days=days - 1)).isoformat()

    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO contracts(title,start_date,end_date,penalty_xp,active,broken,penalty_applied,is_personal)
        VALUES (?,?,?,?,1,0,0,1)
    """, (title, start_iso, end_iso, int(penalty_xp)))
    conn.commit(); conn.close()

# ---- offers (available contracts) ----
def _now_local_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_available_contracts(now_iso: str | None = None):
    if now_iso is None: now_iso = _now_local_iso()
    conn = get_connection(); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    cur.execute("""
        SELECT id,title,expires_at,duration_days,penalty_xp
        FROM contract_offers
        WHERE claimed=0 AND datetime(expires_at) > datetime(?)
        ORDER BY expires_at ASC
    """, (now_iso,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def get_available_offers_count(now_iso: str | None = None) -> int:
    return len(get_available_contracts(now_iso))

def claim_contract_offer(offer_id: int):
    deactivate_expired_and_broken()
    # limits: max 3 active total
    if get_active_contracts_count() >= 3:
        raise ValueError("You already have 3 active contracts.")
    # claim
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT title, duration_days, penalty_xp, expires_at, claimed
        FROM contract_offers WHERE id=?
    """, (offer_id,))
    row = cur.fetchone()
    if not row: conn.close(); raise ValueError("Offer not found.")
    title, duration_days, penalty_xp, expires_at, claimed = row
    # expired or already claimed?
    cur.execute("SELECT datetime(?) <= datetime('now','localtime')", (expires_at,))
    expired = cur.fetchone()[0] == 1
    if expired or claimed:
        conn.close(); raise ValueError("Offer expired or already claimed.")

    start = date.today()
    end = start + _td(days=int(duration_days) - 1)
    cur.execute("""
        INSERT INTO contracts(title,start_date,end_date,penalty_xp,active,broken,penalty_applied,is_personal)
        VALUES (?,?,?,?,1,0,0,0)
    """, (title, start.isoformat(), end.isoformat(), int(penalty_xp)))
    cur.execute("UPDATE contract_offers SET claimed=1 WHERE id=?", (offer_id,))
    conn.commit(); conn.close()

# ---- daily generator ----
def generate_daily_contracts_if_needed():
    # Only seed once per day
    last = get_meta("offers_day")
    today = date.today().isoformat()
    if last == today:
        return
    # clear out expired offers (housekeeping)
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM contract_offers WHERE datetime(expires_at) <= datetime('now','localtime') OR claimed=1")
    conn.commit()

    # A few themed templates (tweak to taste)
    templates = [
        ("No social media after 9PM", 3, 150),
        ("Wake up by 7:00 AM", 3, 150),
        ("Journal + meditate 1 hour today", 1, 120),
        ("Three 25-min focus blocks", 1, 120),
        ("10k steps per day", 3, 150),
        ("Protein with every meal", 2, 120),
        ("No sugar drinks", 2, 120),
    ]

    import random, math
    now = datetime.now()
    new_offers = []
    # 3 fresh offers/day; each expires within 6–24h from now
    for _ in range(3):
        title, dur_days, penalty = random.choice(templates)
        expire_hours = random.randint(6, 24)
        expires_at = (now + _td(hours=expire_hours)).strftime("%Y-%m-%d %H:%M:%S")
        new_offers.append((title, expires_at, dur_days, penalty))

    cur.executemany("""
        INSERT INTO contract_offers(title,expires_at,duration_days,penalty_xp,claimed)
        VALUES (?,?,?,?,0)
    """, new_offers)
    conn.commit(); conn.close()
    set_meta("offers_day", today)
    
    # -------- nonnegotiables (Logger) --------
def add_nn_task(date_for: str, text: str):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("INSERT INTO nonnegotiables(date_for, text, completed) VALUES(?,?,0)", (date_for, text.strip()))
    conn.commit(); conn.close()

def get_nn_tasks(date_for: str):
    conn = get_connection(); conn.row_factory = sqlite3.Row; cur = conn.cursor()
    cur.execute("SELECT id, date_for, text, completed FROM nonnegotiables WHERE date_for=? ORDER BY id ASC", (date_for,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close(); return rows

def set_nn_completed(task_id: int, completed: bool):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("UPDATE nonnegotiables SET completed=? WHERE id=?", (1 if completed else 0, int(task_id)))
    conn.commit(); conn.close()

def delete_nn_task(task_id: int):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM nonnegotiables WHERE id=?", (int(task_id),))
    conn.commit(); conn.close()

def nn_result_applied(date_for: str) -> bool:
    return (get_meta(f"nn_applied:{date_for}") is not None)

def set_nn_result_applied(date_for: str, xp_delta: int):
    set_meta(f"nn_applied:{date_for}", str(int(xp_delta)))


