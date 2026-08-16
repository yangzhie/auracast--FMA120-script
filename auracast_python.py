#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

ROUTE_ID = 86

AUDIO_ROOT = Path(
    r"C:\Users\sithm\OneDrive\Desktop\AudioAuracast"
)

MAGIC = b"AU"
PROTOCOL_VERSION = 1

DIRECTION_OUTBOUND = 0
LANGUAGE_ENGLISH = 1


# ============================================================
# STOP MODEL
# ============================================================

@dataclass(frozen=True)
class Stop:
    index: int
    name: str
    folder: str
    audio_stem: str
    direction: int = DIRECTION_OUTBOUND
    language: int = LANGUAGE_ENGLISH


# ============================================================
# ROUTE 86 STOPS
# ============================================================

STOPS = {
    1: Stop(
        index=1,
        name="Stop 1",
        folder="Stop 1",
        audio_stem="audio1"
    ),

    2: Stop(
        index=2,
        name="Stop 2",
        folder="Stop 2",
        audio_stem="audio2"
    ),

    3: Stop(
        index=3,
        name="Stop 3",
        folder="Stop 3",
        audio_stem="audio3"
    ),

    4: Stop(
        index=4,
        name="Stop 4",
        folder="Stop 4",
        audio_stem="audio4"
    )
}


if __name__ == "__main__":

    print(f"Route {ROUTE_ID}")

    for stop in STOPS.values():

        print(
            f"{stop.index}: "
            f"{stop.name} "
            f"({stop.folder}/{stop.audio_stem})"
        )
