# prompts.py
import os, random
from database import get_meta, set_meta

FILE_CANDIDATES = ["journal_prompts.txt", "assets/journal_prompts.txt", "prompts/journal_prompts.txt"]

def _load_prompts():
    path = next((p for p in FILE_CANDIDATES if os.path.exists(p)), None)
    if not path: return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]
    return []

def get_prompt_for_date(day_iso: str):
    key = f"prompt:{day_iso}"
    cached = get_meta(key)
    if cached: return cached
    prompts = _load_prompts()
    if not prompts: return ""
    # deterministic but shuffled feel: rotate by stored index
    idx = get_meta("prompt_idx")
    try: idx = int(idx)
    except: idx = 0
    pick = prompts[idx % len(prompts)]
    set_meta(key, pick)
    set_meta("prompt_idx", str((idx+1) % (len(prompts)*4)))  # move forward
    return pick
