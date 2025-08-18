"""UI package exports for HabitTracker.

This file makes the `ui` directory a proper Python package. It intentionally
keeps the exports small to avoid heavy imports at package-import time.
"""
from .app import HabitTrackerApp  # lazy import in app/__init__.py

__all__ = ["HabitTrackerApp"]
