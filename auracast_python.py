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
    r"./AudioAuracast"
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

        # Check each supported file extension.
        for extension in (
            ".mp3",
            ".mp4",
            ".m4a",
            ".wav"
        ):
            candidate = (
                folder_path
                / f"{self.audio_stem}{extension}"
            )

            if candidate.exists():
                return candidate

        # Return the expected MP3 path if no supported
        # audio file is currently found.
        return (
            folder_path
            / f"{self.audio_stem}.mp3"
        )

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
        Generate a unique Broadcast ID for each stop.

        Route 86 = 0x56

        Stop 1 -> 560001
        Stop 2 -> 560002
        Stop 3 -> 560003
        Stop 4 -> 560004
        """

        return (
            f"{ROUTE_ID:02X}"
            f"00"
            f"{self.index:02X}"
        )


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

    value = (
        value
        .lower()
        .replace("0x", "")
    )

    company_id = int(
        value,
        16
    )

    # Company ID must fit inside 16 bits.
    if not 0 <= company_id <= 0xFFFF:
        raise ValueError(
            "Company ID must fit in 16 bits"
        )

    return company_id


# ============================================================
# PROJECT METADATA
# ============================================================

def build_project_payload(
    stop: Stop
) -> bytes:
    """
    Build the custom Route 86 metadata.

    Layout:

    AU
    |
    +-- Protocol Version
    +-- Route ID
    +-- Stop ID
    +-- Direction
    +-- Language
    +-- Audio ID
    """

    return (
        MAGIC
        + bytes([
            PROTOCOL_VERSION
        ])
        + struct.pack(
            "<H",
            ROUTE_ID
        )
        + bytes([
            stop.index,
            stop.direction,
            stop.language,
            stop.index
        ])
    )


# ============================================================
# BF METADATA ENCODING
# ============================================================

def build_bf_hex(
    stop: Stop,
    company_id: int
) -> str:
    """
    Build the BF manufacturer-specific advertising data.

    Layout:

    Length
      |
    0xFF
      |
    Company ID
      |
    AU
      |
    Protocol Version
      |
    Route ID
      |
    Stop ID
      |
    Direction
      |
    Language
      |
    Audio ID
    """

    # First build our custom project metadata.
    project_payload = (
        build_project_payload(stop)
    )

    # 0xFF identifies manufacturer-specific advertising data.
    # The Company ID is stored in little-endian format.
    after_length = (
        bytes([0xFF])
        + struct.pack(
            "<H",
            company_id
        )
        + project_payload
    )

    # The first byte describes how many bytes follow it.
    full_payload = (
        bytes([
            len(after_length)
        ])
        + after_length
    )

    # FMA120 BF configuration uses hexadecimal text.
    return (
        full_payload
        .hex()
        .upper()
    )


# ============================================================
# BF METADATA DECODING
# ============================================================

def decode_bf_hex(
    bf_hex: str
) -> dict:
    """
    Decode BF hexadecimal data back into
    Route 86 project information.

    This performs the opposite operation
    to build_bf_hex().
    """

    # Convert hexadecimal text back into raw bytes.
    raw = bytes.fromhex(
        bf_hex
    )

    # The first byte should equal the number
    # of bytes that follow it.
    if raw[0] != len(raw) - 1:
        raise ValueError(
            "BF length mismatch"
        )

    # 0xFF means manufacturer-specific data.
    if raw[1] != 0xFF:
        raise ValueError(
            "Not manufacturer-specific data"
        )

    # Extract the Bluetooth Company ID.
    company_id = int.from_bytes(
        raw[2:4],
        "little"
    )

    # Everything after the Company ID is
    # our custom project payload.
    payload = raw[4:]

    # Check whether this data belongs to our project.
    if payload[:2] != MAGIC:
        raise ValueError(
            "Wrong project magic"
        )

    # Extract each field from the project payload.
    return {
        "company_id":
            company_id,

        "version":
            payload[2],

        "route_id":
            int.from_bytes(
                payload[3:5],
                "little"
            ),

        "stop_index":
            payload[5],

        "direction":
            payload[6],

        "language":
            payload[7],

        "audio_id":
            payload[8]
    }


# ============================================================
# NEXT-STOP LOGIC
# ============================================================

def expected_next_stop(
    completed_count: int
) -> Stop | None:
    """
    Determine which stop should be detected next.

    Examples:

    completed_count = 0 -> Stop 1
    completed_count = 1 -> Stop 2
    completed_count = 2 -> Stop 3
    completed_count = 3 -> Stop 4
    completed_count = 4 -> Journey complete
    """

    return STOPS.get(
        completed_count + 1
    )


# ============================================================
# EXPECTED STOP MATCHING
# ============================================================

def matches_expected_stop(
    bf_hex: str,
    expected: Stop
) -> bool:
    """
    Check whether the BF metadata received from
    a transmitter belongs to the expected stop.

    The detected transmitter must have:

    - Correct protocol version
    - Correct Route ID
    - Correct Stop ID
    - Correct direction
    - Correct language
    """

    # Decode the received BF data.
    data = decode_bf_hex(
        bf_hex
    )

    # Compare the decoded transmitter information
    # with the stop the passenger is expecting.
    return (
        data["version"]
        == PROTOCOL_VERSION

        and data["route_id"]
        == ROUTE_ID

        and data["stop_index"]
        == expected.index

        and data["direction"]
        == expected.direction

        and data["language"]
        == expected.language
    )

    
# ============================================================
# TEST CURRENT FEATURES
# ============================================================
 
if __name__ == "__main__":

    # Temporary Company ID used only for testing
    # the metadata generation and decoding.
    test_company_id = 0x1234

    # Simulate detecting the transmitter for Stop 2.
    detected_stop = STOPS[2]

    # Generate Stop 2 BF metadata.
    bf = build_bf_hex(
        detected_stop,
        test_company_id
    )

    print(
        f"BF: {bf}"
    )

    # Decode the generated metadata to confirm
    # that all fields can be recovered correctly.
    print(
        f"Decoded BF: "
        f"{decode_bf_hex(bf)}"
    )

    print()

    # Assume Stop 1 has already been completed.
    # Therefore the expected next stop is Stop 2.
    expected = (
        expected_next_stop(1)
    )

    if expected is not None:

        print(
            f"Expected next stop: "
            f"{expected.name}"
        )

        print(
            "Detected stop matches expected stop:",
            matches_expected_stop(
                bf,
                expected
            )
        )

    else:

        print(
            "Journey complete"
        )
        #FMA120 serial configuration

