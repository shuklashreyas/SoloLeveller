# constants.py
# Soft, gamey palette
COLORS = {
    "BG": "#E9F0FF",
    "CARD": "#F5E6FF",
    "PRIMARY": "#6C63FF",
    "ACCENT": "#00A0B0",
    "TEXT": "#1E293B",
    "WHITE": "#FFFFFF",
    "MUTED": "#94A3B8",
}

# Fonts
FONTS = {
    "h1": ("Helvetica", 20, "bold"),
    "h2": ("Helvetica", 16, "bold"),
    "h3": ("Helvetica", 13, "bold"),
    "body": ("Helvetica", 12),
    "small": ("Helvetica", 10),
    "btn": ("Helvetica", 12, "bold"),
}

# Positive attributes
POSITIVE_TRAITS = [
    "Spiritual", "Physical", "Mindful", "Social",
    "Integrity", "Intellect", "Character"
]

# Seven deadly sins
SINS = ["Pride", "Greed", "Lust", "Envy", "Gluttony", "Wrath", "Sloth"]

# Which positive attribute a sin reduces
SIN_TO_ATTRIBUTE = {
    "Pride": "Character",
    "Greed": "Spiritual",
    "Lust": "Integrity",
    "Envy": "Spiritual",
    "Gluttony": "Physical",
    "Wrath": "Social",
    "Sloth": "Mindful",
}

# Attribute bounds (FIFA-card vibes)
STAT_MIN = 35
STAT_MAX = 99

# Overwatch/RL-style ranks by average stat
RANKS = [
    (35, 44, "Novice"),
    (45, 54, "Apprentice"),
    (55, 64, "Challenger"),
    (65, 74, "Adept"),
    (75, 84, "Disciplined"),
    (85, 92, "Master"),
    (93, 99, "Transcendent"),
]

# Quick menus
ATONE_MENU = {
    "Spiritual": [
        ("Meditation (10m+)", 2), ("Journal or Gratitude", 2),
        ("Prayer / Reflection", 2), ("Nature walk", 2),
        ("Acts of service", 3), ("Read philosophy/spiritual", 2),
        ("Other…", 0),
    ],
    "Physical": [
        ("Workout / Lifting", 3), ("Play a sport", 3),
        ("Cardio (20m+)", 2), ("Walk 10k steps", 2),
        ("Stretch / Mobility", 1), ("Other…", 0),
    ],
    "Mindful": [
        ("Deep work 60+ min", 3), ("Pomodoro 25m", 1),
        ("No social media block", 3), ("Breathing practice", 1),
        ("Other…", 0),
    ],
    "Social": [
        ("Family time", 2), ("Friends / loved ones", 2),
        ("Made a new connection", 2), ("Called someone", 1),
        ("Other…", 0),
    ],
    "Integrity": [
        ("Completed plan/schedule", 3), ("Kept a promise", 2),
        ("Woke up on time", 2), ("Chore / Errand done", 1),
        ("Other…", 0),
    ],
    "Intellect": [
        ("Watched educational pod/vid", 2), ("Read 20+ pages", 2),
        ("Course / Lecture / Class", 3), ("Practice (coding/math etc.)", 2),
        ("Other…", 0),
    ],
    "Character": [
        ("Helped someone", 2), ("Random act of kindness", 2),
        ("Volunteered", 3), ("Apologized / Owned mistake", 2),
        ("Other…", 0),
    ],
}

SIN_MENU = {
    "Pride": [("Bragging / belittling", -2), ("Dismissed feedback", -2), ("Other…", 0)],
    "Greed": [("Cut corners for gain", -3), ("Money-obsessed spiral", -2), ("Other…", 0)],
    "Lust":  [("NSFW rabbit hole", -3), ("Sexual distraction from goals", -2), ("Other…", 0)],
    "Envy":  [("Compared self on LinkedIn/IG", -2), ("Resentment towards peers", -2), ("Other…", 0)],
    "Gluttony": [("Binge eating/junk", -3), ("Sugary drinks excess", -2), ("Other…", 0)],
    "Wrath": [("Angry outburst", -3), ("Online arguments", -2), ("Other…", 0)],
    "Sloth": [("Skipped work/study", -3), ("Procrastinated session", -2), ("Slept way past plan", -2), ("Other…", 0)],
}

# Brief descriptions for the quiz
ATTR_DESCRIPTIONS = {
    "Spiritual": "Meditation, gratitude, nature, prayer, journaling, service.",
    "Physical":  "Workout, sport, cardio, steps, stretching, mobility.",
    "Mindful":   "Deep work, focus blocks, low distraction, breathing practice.",
    "Social":    "Family/friends time, connection, calls.",
    "Integrity": "Doing what you said, punctuality, chores/errands.",
    "Intellect": "Reading, course/lectures, deliberate practice, learning.",
    "Character": "Helping others, kindness, volunteering, owning mistakes.",
}
