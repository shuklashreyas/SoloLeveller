# bgm.py — background music shuffler for Tkinter apps (non-blocking)
# Best with: pip install pygame

import os, random, threading, time
try:
    import pygame
except Exception:
    pygame = None  # we'll no-op if pygame isn't present

_SEARCH_DIRS = [".", "soundeffects", "audio", "assets", "assets/music", "bgm", "music"]
_DEFAULT_NAMES = ["bgmusic.mp3", "bgmusic2.mp3", "bgmusic3.mp3",
                  "bgmusic4.mp3", "bgmusic5.mp3", "bgmusic6.mp3",
                  "bgmusic7.mp3", "bgmusic8.mp3"]

_playlist = []
_last_idx = None
_stop_event = threading.Event()
_worker = None
_init_done = False

def _resolve_candidates(names):
    out = []
    for nm in names:
        for d in _SEARCH_DIRS:
            p = os.path.join(d, nm)
            if os.path.exists(p):
                out.append(os.path.abspath(p))
                break
    return out

def init_bgm():
    """Initialize pygame mixer once."""
    global _init_done
    if _init_done or pygame is None:
        _init_done = True
        return
    try:
        pygame.mixer.init()
    except Exception:
        pass
    _init_done = True

def _choose_next():
    global _last_idx
    if not _playlist:
        return None
    choices = list(range(len(_playlist)))
    if _last_idx is not None and len(choices) > 1:
        choices.remove(_last_idx)
    idx = random.choice(choices)
    _last_idx = idx
    return _playlist[idx]

def _thread_loop(volume, crossfade_ms):
    if pygame is None:
        return  # no pygame installed; silently do nothing
    while not _stop_event.is_set():
        busy = False
        try:
            busy = pygame.mixer.music.get_busy()
        except Exception:
            busy = False
        if not busy:
            nxt = _choose_next()
            if nxt:
                try:
                    pygame.mixer.music.fadeout(crossfade_ms)
                except Exception:
                    pass
                try:
                    pygame.mixer.music.load(nxt)
                    pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))
                    pygame.mixer.music.play(loops=0, fade_ms=crossfade_ms)
                except Exception:
                    pass
        # Check a few times per second
        _stop_event.wait(0.5)

def start_bgm_shuffle(names=None, volume=0.25, crossfade_ms=600):
    """
    Start shuffling the given track names (searching common folders).
    If names is None, uses ["bgmusic.mp3", "bgmusic2.mp3", "bgmusic3.mp3"].
    """
    global _playlist, _worker
    init_bgm()
    if names is None:
        names = _DEFAULT_NAMES
    _playlist = _resolve_candidates(names)
    if not _playlist or pygame is None:
        return  # nothing to play or pygame not available
    stop_bgm()  # ensure previous thread stopped
    _stop_event.clear()
    _worker = threading.Thread(target=_thread_loop, args=(volume, crossfade_ms), daemon=True)
    _worker.start()

def stop_bgm(fade_ms=400):
    """Stop playback and terminate the background thread."""
    if pygame is not None:
        try:
            pygame.mixer.music.fadeout(fade_ms)
        except Exception:
            pass
    _stop_event.set()

def set_bgm_volume(v):
    if pygame is not None:
        try:
            pygame.mixer.music.set_volume(max(0.0, min(1.0, float(v))))
        except Exception:
            pass
