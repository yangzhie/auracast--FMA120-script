#!/usr/bin/env python3
from __future__ import annotations

import struct
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

        for extension in (".mp3", ".mp4", ".m4a", ".wav"):
            candidate = folder_path / f"{self.audio_stem}{extension}"

            if candidate.exists():
                return candidate

        return folder_path / f"{self.audio_stem}.mp3"

    @property
    def broadcast_name(self) -> str:
        """
        Human-readable Auracast broadcast name.

        Examples:
        Stop 1 -> AURA86-S1
        Stop 2 -> AURA86-S2
        """
        return f"AURA86-S{self.index}"

    @property
    def broadcast_id(self) -> str:
        """
        Generate a unique broadcast ID for each stop.

        Route 86 = 0x56:
        Stop 1 -> 560001
        Stop 2 -> 560002
        Stop 3 -> 560003
        Stop 4 -> 560004
        """
        return f"{ROUTE_ID:02X}00{self.index:02X}"


# ============================================================
# ROUTE 86 STOPS
# ============================================================

STOPS = {
    1: Stop(1, "Stop 1", "Stop 1", "audio1"),
    2: Stop(2, "Stop 2", "Stop 2", "audio2"),
    3: Stop(3, "Stop 3", "Stop 3", "audio3"),
    4: Stop(4, "Stop 4", "Stop 4", "audio4"),
}


# ============================================================
# COMPANY ID
# ============================================================

def parse_company_id(value: str) -> int:
    """
    Parse a hexadecimal Bluetooth Company ID.

    Examples:
        "1234"
        "0x1234"
    """
    value = value.lower().replace("0x", "")
    company_id = int(value, 16)

    if not 0 <= company_id <= 0xFFFF:
        raise ValueError("Company ID must fit in 16 bits")

    return company_id


# ============================================================
# PROJECT METADATA
# ============================================================

def build_project_payload(stop: Stop) -> bytes:
    """
    Build the custom project payload.

    Layout:
        AU | version | route_id (little-endian) |
        stop_id | direction | language | audio_id
    """
    return (
        MAGIC
        + bytes([PROTOCOL_VERSION])
        + struct.pack("<H", ROUTE_ID)
        + bytes([
            stop.index,
            stop.direction,
            stop.language,
            stop.index,
        ])
    )


# ============================================================
# BF METADATA
# ============================================================

def build_bf_hex(stop: Stop, company_id: int) -> str:
    """
    Build the BF manufacturer-specific advertising data.

    Layout:
        Length
        0xFF
        Company ID (little-endian)
        Project payload
    """
    project_payload = build_project_payload(stop)

    after_length = (
        bytes([0xFF])
        + struct.pack("<H", company_id)
        + project_payload
    )

    full_payload = bytes([len(after_length)]) + after_length

    return full_payload.hex().upper()


# ============================================================
# TEST CURRENT FEATURES
# ============================================================

if __name__ == "__main__":
    # Temporary Company ID used only to demonstrate BF generation.
    test_company_id = 0x1234

    print(f"Route {ROUTE_ID}")
    print()

    for stop in STOPS.values():
        bf = build_bf_hex(stop, test_company_id)

        print(f"Stop: {stop.index}")
        print(f"Broadcast Name: {stop.broadcast_name}")
        print(f"Broadcast ID: {stop.broadcast_id}")
        print(f"Audio: {stop.audio_path}")
        print(f"BF: {bf}")
        print()
