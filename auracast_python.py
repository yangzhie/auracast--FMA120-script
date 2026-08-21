#!/usr/bin/env python3
from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from pathlib import Path

import serial
from serial.tools import list_ports


# ============================================================
# PROJECT CONFIGURATION
# ============================================================

ROUTE_ID = 86

# Shared Broadcast Code used by all four stops in the current PoC.
SHARED_BROADCAST_CODE = "AURA86DEMO2026"

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
# FMA120 SERIAL CONTROL
# ============================================================

class FMA120:
    """Control one physical FMA120 through its serial / COM port."""

    def __init__(self, port: str):
        """Open the FMA120 serial control connection."""
        self.ser = serial.Serial(
            port,
            921600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=2,
            write_timeout=2
        )
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def close(self):
        """Close the serial connection."""
        self.ser.close()

    def command(self, body: str) -> list[str]:
        """Send a BC command and return the FMA120 response lines."""
        # Commands are sent as: BC:<command> followed by CRLF.
        packet = f"BC:{body}\r\n".encode("ascii")
        print(f"TX  BC:{body}")
        self.ser.write(packet)
        self.ser.flush()

        responses = []
        while True:
            raw = self.ser.readline()
            if not raw:
                break

            text = raw.decode("ascii", errors="replace").strip()
            if text:
                print(f"RX  {text}")
                responses.append(text)

        return responses

    def require_ok(self, body: str):
        """Send a command and require an OK response."""
        responses = self.command(body)
        if "OK" not in responses:
            raise RuntimeError(
                f"No OK for BC:{body}; got {responses}"
            )

    def provision(self, stop: Stop, company_id: int):
        """
        Configure this FMA120 as one Route 86 stop.

        BN = Broadcast Name
        BE = Broadcast Code
        BI = Broadcast ID
        BF = Route / stop metadata
        """
        # Generate the custom BF metadata for this stop.
        bf = build_bf_hex(stop, company_id)

        # 1. Set the human-readable Broadcast Name.
        self.require_ok(f"BN={stop.broadcast_name}")

        # 2. Set the shared Broadcast Code used by the PoC.
        self.require_ok(f"BE={SHARED_BROADCAST_CODE}")

        # 3. Set the unique Broadcast ID for this stop.
        self.require_ok(f"BI={stop.broadcast_id}")

        # 4. Set the custom BF metadata containing Route and Stop IDs.
        self.require_ok(f"BF={bf}")

        # Read values back to verify the configuration.
        print("Verification:")
        self.command("BN")
        self.command("BI")
        self.command("BF")


# ============================================================
# SERIAL PORT DISCOVERY
# ============================================================

def list_serial_ports():
    """List serial / COM ports so the FMA120 port can be identified."""
    for port in list_ports.comports():
        print(port.device, port.description)


# ============================================================
# AUDIO DEVICE DISCOVERY
# ============================================================

def list_audio_devices():
    """
    Display the available audio output devices.

    The main purpose is to identify the FMA120
    USB audio output so Python can send the
    correct stop announcement to the transmitter.
    """

    import pygame

    from pygame._sdl2 import (
        audio as sdl2_audio
    )

    # Initialise pygame so audio devices can be queried.
    pygame.init()

    # False means output / playback devices.
    devices = (
        sdl2_audio
        .get_audio_device_names(
            False
        )
    )

    for index, name in enumerate(
        devices
    ):

        print(
            f"[{index}] {name}"
        )


# ============================================================
# AUDIO PLAYBACK
# ============================================================

def play_audio(
    stop: Stop,
    audio_device: str | None,
    once: bool = False
):
    """
    Play the audio file associated with a stop.

    The selected audio output should normally be
    the FMA120 USB audio device.

    Signal flow:

        audio file
            |
            v
        Python / pygame
            |
            v
        FMA120 USB Audio
            |
            v
        FMA120
            |
            v
        Auracast broadcast

    If once=False, the announcement loops.
    If once=True, it plays one time only.
    """

    import pygame

    # Automatically resolve the audio file for
    # the selected stop.
    audio_file = (
        stop.audio_path
    )

    # Stop immediately if the audio file does
    # not exist.
    if not audio_file.exists():

        raise FileNotFoundError(
            audio_file
        )

    # Reset any existing mixer session before
    # selecting a new output device.
    pygame.mixer.quit()

    # Initialise the audio output.
    pygame.mixer.init(
        frequency=48000,
        size=-16,
        channels=2,
        buffer=1024,
        devicename=audio_device
    )

    # Load the stop announcement.
    pygame.mixer.music.load(
        str(audio_file)
    )

    # Play once or loop continuously.
    pygame.mixer.music.play(
        0 if once else -1
    )

    print(
        f"Playing {audio_file} "
        f"-> "
        f"{audio_device or 'default output'}"
    )

    print(
        "Press Ctrl+C to stop"
    )

    try:

        # Keep the Python process alive while
        # the audio is playing.
        while (
            pygame
            .mixer
            .music
            .get_busy()
        ):

            time.sleep(
                0.25
            )

    except KeyboardInterrupt:

        # Ctrl+C allows the user to stop playback.
        pass

    finally:

        # Always stop and release the mixer cleanly.
        pygame.mixer.music.stop()
        pygame.mixer.quit()


# ============================================================
# TEST CURRENT FEATURES
# ============================================================

if __name__ == "__main__":

    # Temporary Company ID used only for
    # metadata testing.
    test_company_id = 0x1234

    # Use Stop 2 as an example.
    stop = STOPS[2]

    # Build Stop 2 BF metadata.
    bf = build_bf_hex(
        stop,
        test_company_id
    )

    print(
        f"Route: {ROUTE_ID}"
    )

    print(
        f"Stop: {stop.name}"
    )

    print(
        f"Broadcast Name: "
        f"{stop.broadcast_name}"
    )

    print(
        f"Broadcast Code: "
        f"{SHARED_BROADCAST_CODE}"
    )

    print(
        f"Broadcast ID: "
        f"{stop.broadcast_id}"
    )

    print(
        f"BF: {bf}"
    )

    print(
        f"Decoded BF: "
        f"{decode_bf_hex(bf)}"
    )

    print(
        "\nAvailable serial ports:"
    )

    list_serial_ports()

    print(
        "\nAvailable audio output devices:"
    )

    # This shows the available playback devices.
    # The user can identify the FMA120 USB audio
    # output from this list.
    try:
        list_audio_devices()

    except Exception as error:

        # Keep metadata/serial testing usable even
        # if pygame or an audio device is unavailable.
        print(
            f"Could not list audio devices: {error}"
        )

    print(
        "\nAudio playback support is ready."
    )

    print(
        "The full play/provision/run commands "
        "will be connected through the CLI "
        "in the next commit."
    )
