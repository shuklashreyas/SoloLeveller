# constants.py

# ---------- Palettes ----------
def _shade(hex_color, factor=0.9):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return f"#{r:02X}{g:02X}{b:02X}"

PALETTES = {
    # Your original soft/gamey palette, now selectable by name
    "Soft Gamey": {"BG": "#E9F0FF", "CARD": "#F5E6FF", "PRIMARY": "#6C63FF", "ACCENT": "#00A0B0",
                   "TEXT": "#1E293B", "MUTED": "#94A3B8"},
    "Aurora Synth": {"BG": "#0B0F1A", "CARD": "#111827", "PRIMARY": "#7C3AED", "ACCENT": "#22D3EE",
                     "TEXT": "#E5E7EB", "MUTED": "#94A3B8"},
    "Sunset Soda":  {"BG": "#0B0C22", "CARD": "#14143A", "PRIMARY": "#FF5C8A", "ACCENT": "#FFD166",
                     "TEXT": "#F1F5F9", "MUTED": "#94A3B8"},
    "Royal Indigo": {"BG": "#F6F7FB", "CARD": "#ECEFF5", "PRIMARY": "#4F46E5", "ACCENT": "#06B6D4",
                     "TEXT": "#111827", "MUTED": "#6B7280"},
    "Forest Sage":  {"BG": "#F3F6F3", "CARD": "#E8F0EA", "PRIMARY": "#2E7D32", "ACCENT": "#3B82F6",
                     "TEXT": "#0F172A", "MUTED": "#64748B"},
    "Blush Noir":   {"BG": "#0F1014", "CARD": "#16181E", "PRIMARY": "#F472B6", "ACCENT": "#60A5FA",
                     "TEXT": "#E5E7EB", "MUTED": "#9CA3AF"},
    "Slate Mono":   {"BG": "#F8FAFC", "CARD": "#EEF2F7", "PRIMARY": "#334155", "ACCENT": "#0EA5E9",
                     "TEXT": "#0F172A", "MUTED": "#64748B"},
}

THEME = "Soft Gamey"  # default; overridden by DB at runtime

# --- Contrast helpers ---
def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def _srgb_to_linear(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def _rel_lum(hex_color: str):
    r, g, b = _hex_to_rgb(hex_color)
    R, G, B = map(_srgb_to_linear, (r, g, b))
    return 0.2126 * R + 0.7152 * G + 0.0722 * B

def _contrast(a_hex: str, b_hex: str):
    L1, L2 = _rel_lum(a_hex), _rel_lum(b_hex)
    Lh, Ll = (L1, L2) if L1 > L2 else (L2, L1)
    return (Lh + 0.05) / (Ll + 0.05)

def _best_fg_on(bg_hex: str):
    # Pick whatever gives higher contrast on the background.
    black = "#0B0F19"   # deep slate (nicer than pure black)
    white = "#FFFFFF"
    return black if _contrast(bg_hex, black) >= _contrast(bg_hex, white) else white

def _blend_hex(fg_hex: str, bg_hex: str, t: float):
    # linear blend for a "muted" tone (0..1 toward bg)
    fr, fgc, fb = _hex_to_rgb(fg_hex); br, bgc, bb = _hex_to_rgb(bg_hex)
    r = int(fr * (1 - t) + br * t)
    g = int(fgc * (1 - t) + bgc * t)
    b = int(fb * (1 - t) + bb * t)
    return f"#{r:02X}{g:02X}{b:02X}"


def _derive(base):
    return {
        **base,
        "PRIMARY_HOVER": _shade(base["PRIMARY"], 0.92),
        "PRIMARY_ACTIVE": _shade(base["PRIMARY"], 0.84),
        "ACCENT_HOVER": _shade(base["ACCENT"], 0.92),
        "ACCENT_ACTIVE": _shade(base["ACCENT"], 0.84),
        "WHITE": "#FFFFFF",
    }

COLORS = {}
COLORS.update(_derive(PALETTES[THEME]))

def _apply_semantic_defaults():
    # Theme-agnostic colors used by components
    COLORS.setdefault("GOOD",  "#22C55E")  # green for gains
    COLORS.setdefault("BAD",   "#EF4444")  # red for losses
    COLORS.setdefault("TRACK", "#D4D4D8")  # neutral track for bars
    COLORS.setdefault("MUTED", "#94A3B8")  # ensure exists even if palette forgot

_apply_semantic_defaults()

def set_theme(name: str):
    global COLORS
    pal = PALETTES.get(name)
    if not pal:
        return

    # Start with the palette as given
    COLORS.update(pal)

    # Ensure required keys exist (fallbacks)
    COLORS.setdefault("BG", "#0F1115")
    COLORS.setdefault("CARD", "#171A21")
    COLORS.setdefault("PRIMARY", "#7C3AED")
    COLORS.setdefault("ACCENT", "#22D3EE")
    COLORS.setdefault("WHITE", "#FFFFFF")  # keep a true white around
    COLORS.setdefault("TRACK", "#D4D4D8")  # progressbar trough default

    # --- Auto-choose readable text colors ---
    # Main text on BG
    COLORS["TEXT"] = _best_fg_on(COLORS["BG"])
    # Muted = a blend toward BG for subtle labels (keeps contrast on both light/dark)
    COLORS["MUTED"] = _blend_hex(COLORS["TEXT"], COLORS["BG"], 0.4)

    # Derive preferred foregrounds for filled buttons/cards if you want to use them
    COLORS["PRIMARY_TEXT"] = _best_fg_on(COLORS["PRIMARY"])
    COLORS["ACCENT_TEXT"]  = _best_fg_on(COLORS["ACCENT"])
    COLORS["CARD_TEXT"]    = _best_fg_on(COLORS["CARD"])

    # Row backgrounds for list/tree views (gentle contrast from CARD)
    # blend slightly toward BG so rows are visible on both light and dark themes
    COLORS.setdefault("ROW_ODD", _blend_hex(COLORS["CARD"], COLORS["BG"], 0.06))
    COLORS.setdefault("ROW_EVEN", _blend_hex(COLORS["CARD"], COLORS["BG"], 0.12))

    # Optional: hovers (keep if you already define them; these are safe fallbacks)
    COLORS.setdefault("PRIMARY_HOVER", COLORS["PRIMARY"])
    COLORS.setdefault("ACCENT_HOVER", COLORS["ACCENT"])


# ---------- Fonts ----------
FONTS = {
    "h1": ("Helvetica", 20, "bold"),
    "h2": ("Helvetica", 16, "bold"),
    "h3": ("Helvetica", 13, "bold"),
    "body": ("Helvetica", 12),
    "small": ("Helvetica", 10),
    "btn": ("Helvetica", 12, "bold"),
}

# ---------- Traits/Sins ----------
POSITIVE_TRAITS = [
    "Spiritual", "Physical", "Mindful", "Social",
    "Integrity", "Intellect", "Character"
]

SINS = ["Pride", "Greed", "Lust", "Envy", "Gluttony", "Wrath", "Sloth"]

SIN_TO_ATTRIBUTE = {
    "Pride": "Character",
    "Greed": "Spiritual",
    "Lust": "Integrity",
    "Envy": "Spiritual",
    "Gluttony": "Physical",
    "Wrath": "Social",
    "Sloth": "Mindful",
}

# ---------- Stats / Ranks ----------
STAT_MIN = 35
STAT_MAX = 99

RANKS = [
    (35, 44, "Novice"),
    (45, 54, "Apprentice"),
    (55, 64, "Challenger"),
    (65, 74, "Adept"),
    (75, 84, "Disciplined"),
    (85, 92, "Master"),
    (93, 99, "Transcendent"),
]

# ---------- Menus ----------
ATONE_MENU = {
    "Spiritual": [
        ("Meditation (10m+)", 2),
        ("Journal or Gratitude", 2),
        ("Prayer / Reflection", 2),
        ("Nature walk", 2),
        ("Acts of service", 3),
        ("Read philosophy/spiritual", 2),
        ("Mindful silence for 5+ minutes", 1),
        ("Read a sacred or inspiring text", 2),
        ("Practice forgiveness towards someone", 3),
        ("Volunteer at a community or faith event", 3),
        ("Limit news/social media for mental clarity", 2),
        ("Attend a religious or spiritual gathering", 2),
        ("Other…", 0),
    ],
    "Physical": [
        ("Workout / Lifting", 3),
        ("Play a sport", 3),
        ("Cardio (20m+)", 2),
        ("Walk 10k steps", 2),
        ("Stretch / Mobility", 1),
        ("Cook a healthy meal from scratch", 2),
        ("Go for a hike or outdoor run", 2),
        ("Drink 2+ liters of water", 1),
        ("Complete a challenging fitness goal", 3),
        ("Dance session (10m+)", 2),
        ("Other…", 0),
    ],
    "Mindful": [
        ("Deep work 60+ min", 3),
        ("Pomodoro 25m", 1),
        ("No social media block", 3),
        ("Breathing practice", 1),
        ("Digital detox (1hr+ no devices)", 2),
        ("Single-task focus (finish without multitasking)", 2),
        ("Mindful eating (no distractions)", 2),
        ("Body scan meditation", 1),
        ("Complete an art/creative project", 2),
        ("Plan day ahead intentionally", 2),
        ("Other…", 0),
    ],
    "Social": [
        ("Family time", 2),
        ("Friends / loved ones", 2),
        ("Made a new connection", 2),
        ("Called someone", 1),
        ("Write a thank-you note or message", 2),
        ("Host or attend a gathering", 2),
        ("Mentor or coach someone", 3),
        ("Express genuine appreciation in person", 2),
        ("Help a friend with a task", 3),
        ("Reconnect with someone you lost touch with", 2),
        ("Other…", 0),
    ],
    "Integrity": [
        ("Completed plan/schedule", 3),
        ("Kept a promise", 2),
        ("Woke up on time", 2),
        ("Chore / Errand done", 1),
        ("Paid a bill or debt on time", 2),
        ("Followed through on a difficult commitment", 3),
        ("Organized a messy space", 1),
        ("Finished something you’ve been putting off", 2),
        ("Followed your budget for the day", 2),
        ("Returned something borrowed promptly", 2),
        ("Other…", 0),
    ],
    "Intellect": [
        ("Watched educational pod/vid", 2),
        ("Read 20+ pages", 2),
        ("Course / Lecture / Class", 3),
        ("Practice (coding/math etc.)", 2),
        ("Learned a new skill", 3),
        ("Listened to an educational audiobook", 2),
        ("Took detailed notes on a topic", 2),
        ("Solved a challenging puzzle/problem", 2),
        ("Studied a foreign language", 2),
        ("Taught someone a skill or concept", 3),
        ("Other…", 0),
    ],
    "Character": [
        ("Helped someone", 2),
        ("Random act of kindness", 2),
        ("Volunteered", 3),
        ("Apologized / Owned mistake", 2),
        ("Gave constructive feedback kindly", 2),
        ("Listened without interrupting", 2),
        ("Defended someone treated unfairly", 3),
        ("Shared resources with someone in need", 3),
        ("Stood up for your values respectfully", 3),
        ("Encouraged someone’s goal or dream", 2),
        ("Other…", 0),
    ],
}

SIN_MENU = {
    "Pride": [
        ("Bragging / belittling", -2),
        ("Dismissed feedback", -2),
        ("Taking excessive selfies / mirror checking", -2),
        ("Name-dropping / bragging in conversation", -2),
        ("Refusing to ask for directions", -1),
        ("Interrupting to correct minor details", -1),
        ("Posting achievements for validation", -2),
        ("Refusing to apologize when wrong", -3),
        ("Looking down on others' lifestyles", -2),
        ("Overestimating own abilities", -2),
        ("Taking credit for group efforts", -3),
        ("Other…", 0),
    ],
    "Greed": [
        ("Cut corners for gain", -3),
        ("Money-obsessed spiral", -2),
        ("Hoarding unnecessary items", -2),
        ("Choosing cheapest option regardless of ethics", -2),
        ("Refusing to tip service workers", -2),
        ("Taking extra free samples/condiments", -1),
        ("Not sharing when you have plenty", -2),
        ("Obsessing over money/possessions", -2),
        ("Keeping borrowed items too long", -1),
        ("Buying just because it's on sale", -1),
        ("Avoiding charity despite surplus", -3),
        ("Other…", 0),
    ],
    "Lust": [
        ("NSFW rabbit hole", -3),
        ("Sexual distraction from goals", -2),
        ("Compulsive pornography consumption", -3),
        ("Flirting despite relationship", -3),
        ("Reducing people to appearance", -2),
        ("Excessive dating app use for validation", -2),
        ("Inappropriate comments about bodies", -2),
        ("Cheating emotionally or physically", -3),
        ("Using others for gratification", -3),
        ("Objectifying strangers/celebrities", -2),
        ("Prioritizing looks over character", -1),
        ("Risky sexual behavior for thrills", -3),
        ("Other…", 0),
    ],
    "Envy": [
        ("Compared self on LinkedIn/IG", -2),
        ("Resentment towards peers", -2),
        ("Bitterness at others' promotions", -2),
        ("Gossiping about misfortunes", -2),
        ("Undermining colleagues' success", -3),
        ("Anger at others' recognition", -2),
        ("Copying others' style/ideas", -1),
        ("Passive-aggressive comments", -2),
        ("Depressed by lifestyle posts", -2),
        ("Secretly hoping others fail", -3),
        ("Complaining about 'unfair' advantages", -2),
        ("Other…", 0),
    ],
    "Gluttony": [
        ("Binge eating/junk", -3),
        ("Sugary drinks excess", -2),
        ("Eating past fullness", -2),
        ("Binge-watching TV for hours", -2),
        ("Buying excessive clothes", -2),
        ("Mindless social scrolling", -2),
        ("Over-ordering food", -2),
        ("Drinking alcohol excessively", -3),
        ("Shopping for entertainment", -2),
        ("Accumulating unused hobbies/items", -2),
        ("Taking seconds before others", -1),
        ("Compulsive content consumption", -2),
        ("Other…", 0),
    ],
    "Wrath": [
        ("Angry outburst", -3),
        ("Online arguments", -2),
        ("Road rage / aggressive driving", -3),
        ("Temper over minor issues", -2),
        ("Holding grudges long-term", -2),
        ("Silent treatment as punishment", -2),
        ("Spreading rumors", -3),
        ("Breaking/throwing objects", -3),
        ("Yelling at service workers", -3),
        ("Seeking revenge", -3),
        ("Sarcasm/passive-aggression to hurt", -2),
        ("Other…", 0),
    ],
    "Sloth": [
        ("Skipped work/study", -3),
        ("Procrastinated session", -2),
        ("Slept way past plan", -2),
        ("Procrastinating important tasks repeatedly", -2),
        ("Choosing convenience over ethics", -2),
        ("Avoiding exercise despite need", -2),
        ("Ignoring commitments", -2),
        ("Letting chores pile up", -2),
        ("Entertainment over growth", -2),
        ("Avoiding difficult conversations", -2),
        ("Not following through on promises", -2),
        ("Taking shortcuts hurting quality", -2),
        ("Remaining willfully ignorant", -2),
        ("Other…", 0),
    ],
}


# ---------- Quiz blurbs ----------
ATTR_DESCRIPTIONS = {
    "Spiritual": "Meditation, gratitude, nature, prayer, journaling, service.",
    "Physical":  "Workout, sport, cardio, steps, stretching, mobility.",
    "Mindful":   "Deep work, focus blocks, low distraction, breathing practice.",
    "Social":    "Family/friends time, connection, calls.",
    "Integrity": "Doing what you said, punctuality, chores/errands.",
    "Intellect": "Reading, course/lectures, deliberate practice, learning.",
    "Character": "Helping others, kindness, volunteering, owning mistakes.",
}
