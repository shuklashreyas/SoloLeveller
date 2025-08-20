# sound.py — tiny non-blocking SFX helper for Tkinter apps using mp3 files.
# Best with:  pip install pygame
# Falls back to: macOS 'afplay' or playsound (non-blocking thread)

import os, threading, platform, subprocess

_MUTED = False

def set_muted(flag: bool):
    """Master mute for all sound effects."""
    global _MUTED
    _MUTED = bool(flag)

SFX_FILES = {
    "click":     "click.mp3",
    "levelUp":   "levelUp.mp3",
    "statsDown": "statsDown.mp3",
    "statsUp":   "statsUp.mp3",
    "bought":    "bought.mp3",
}

# Resolve ./soundeffects/<file>
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEF_DIR = os.path.join(BASE_DIR, "soundeffects")

_backend = None
_sounds = {}

def _file_path(name: str):
    fn = SFX_FILES.get(name)
    if not fn: return None
    p = os.path.join(DEF_DIR, fn)
    return p if os.path.exists(p) else None

def init():
    """Pick a backend and (if pygame) pre-load sounds."""
    global _backend
    if _backend is not None:
        return
    try:
        import pygame
        pygame.mixer.init()
        for key in SFX_FILES:
            fp = _file_path(key)
            if fp:
                _sounds[key] = pygame.mixer.Sound(fp)
        _backend = "pygame"
        return
    except Exception:
        pass
    # macOS system player as a decent fallback
    if platform.system() == "Darwin":
        _backend = "afplay"
    else:
        _backend = "playsound"

def play_sfx(name: str):
    if _MUTED:
        return
    """Play a short effect asynchronously. Silently no-ops if unavailable."""
    fp = _file_path(name)
    # If not found in SFX_FILES, treat as direct file path (e.g., 'soundeffects/bought.mp3')
    if not fp and os.path.exists(name):
        fp = name
    if not fp:
        return
    try:
        if _backend is None:
            init()
        if _backend == "pygame":
            import pygame  # safe, we succeeded earlier
            snd = _sounds.get(name)
            (snd or pygame.mixer.Sound(fp)).play()
        elif _backend == "afplay":
            threading.Thread(target=lambda: subprocess.run(["afplay", fp], check=False),
                             daemon=True).start()
        else:
            try:
                from playsound import playsound
                threading.Thread(target=playsound, args=(fp,), kwargs={"block": False},
                                 daemon=True).start()
            except Exception:
                pass
    except Exception:
        # Never explode the UI because audio failed
        pass


# note: no stop_sfx helper — playbacks are fire-and-forget across backends
