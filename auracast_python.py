#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

ROUTE_ID = 86

AUDIO_ROOT = Path(
    r"\AudioAuracast"
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

    @property
    def audio_path(self) -> Path:
        """
        Automatically find the audio file for this stop.

        Supported formats:
        .mp3
        .mp4
        .m4a
        .wav
        """

        folder_path = AUDIO_ROOT / self.folder

        for extension in (
            ".mp3",
            ".mp4",
            ".m4a",
            ".wav"
        ):
            candidate = folder_path / f"{self.audio_stem}{extension}"

            if candidate.exists():
                return candidate

        # Return the expected MP3 path if no file was found.
        # This keeps later error messages meaningful.
        return folder_path / f"{self.audio_stem}.mp3"


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
            f"{stop.name}"
        )

        print(
            f"Audio: {stop.audio_path}"
        )

        print()
