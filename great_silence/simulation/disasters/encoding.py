"""Binary disaster encoding for efficient storage and transmission.

Encodes disaster events into compact 24-byte binary format.
"""

import struct
import numpy as np
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..engine import HazardEvent

DISASTER_BINARY_FORMAT = "<fBhhhhbbbBBBxxxxx"
EVENT_TYPE_MAP = {"sn": 0, "supernova": 0, "grb": 1, "nsm": 2}
EVENT_TYPE_REVERSE = {0: "sn", 1: "grb", 2: "nsm"}


@dataclass
class DisasterBinary:
    """Compact binary representation of disaster event.

    Layout (24 bytes):
        time_myr:        float32  (4 bytes) - simulation time
        event_type:      uint8    (1 byte)  - 0=SN, 1=GRB, 2=NSM
        position_x:      int16    (2 bytes) - kpc * 1000
        position_y:      int16    (2 bytes)
        position_z:      int16    (2 bytes)
        lethal_radius:   int16    (2 bytes) - pc (integer precision)
        jet_dir_x:       int8     (1 byte)  - unit vector * 127
        jet_dir_y:       int8     (1 byte)
        jet_dir_z:       int8     (1 byte)
        beam_angle_deg:  uint8    (1 byte)  - degrees
        energy_log10:    uint8    (1 byte)  - log10(energy/1e50) + 50
        flags:           uint8    (1 byte)  - bit flags

    Flags:
        bit 0: permanent_sterilization
        bit 1: has_opposing_jet
        bit 2-7: reserved
    """

    time_myr: float
    event_type: int
    position: np.ndarray
    lethal_radius: int
    jet_direction: np.ndarray
    beam_angle_deg: int
    energy: float
    flags: int


def encode_disaster(event: "HazardEvent") -> bytes:
    """Encode HazardEvent to 24-byte binary.

    Args:
        event: Full HazardEvent object

    Returns:
        24 bytes of packed data
    """
    event_type = EVENT_TYPE_MAP.get(event.event_type.lower(), 0)

    pos_x, pos_y, pos_z = np.clip(
        event.position * 1000, -32768, 32767
    ).astype(np.int16)

    lethal_r = int(event.sterilization_radius_pc)
    lethal_r = np.clip(lethal_r, -32768, 32767)

    if hasattr(event, "jet_direction"):
        jet_x, jet_y, jet_z = np.clip(
            event.jet_direction * 127, -127, 127
        ).astype(np.int8)
    else:
        jet_x = jet_y = jet_z = 0

    if hasattr(event, "beam_angle_deg"):
        beam_angle = int(np.clip(event.beam_angle_deg, 0, 255))
    else:
        beam_angle = 0

    energy_log10 = int(np.clip(
        np.log10(event.energy / 1e50) + 50, 0, 255
    ))

    flags = event.flags if hasattr(event, "flags") else 0

    return struct.pack(
        DISASTER_BINARY_FORMAT,
        event.time_myr,
        event_type,
        pos_x,
        pos_y,
        pos_z,
        lethal_r,
        jet_x,
        jet_y,
        jet_z,
        beam_angle,
        energy_log10,
        flags,
    )


def decode_disaster(data: bytes) -> DisasterBinary:
    """Decode 24-byte binary to DisasterBinary.

    Args:
        data: 24+ bytes of packed data

    Returns:
        DisasterBinary with decoded fields
    """
    unpacked = struct.unpack(DISASTER_BINARY_FORMAT, data[:24])

    (
        time_myr,
        event_type,
        pos_x,
        pos_y,
        pos_z,
        lethal_r,
        jet_x,
        jet_y,
        jet_z,
        beam_angle,
        energy_log10,
        flags,
    ) = unpacked

    position = np.array([pos_x, pos_y, pos_z], dtype=np.float32) / 1000.0

    jet_dir = np.array([jet_x, jet_y, jet_z], dtype=np.float32) / 127.0

    jet_dir_norm = np.linalg.norm(jet_dir)
    if jet_dir_norm > 0:
        jet_dir = jet_dir / jet_dir_norm

    energy = 10.0 ** (energy_log10 - 50) * 1e50

    return DisasterBinary(
        time_myr=float(time_myr),
        event_type=int(event_type),
        position=position,
        lethal_radius=int(lethal_r),
        jet_direction=jet_dir,
        beam_angle_deg=int(beam_angle),
        energy=float(energy),
        flags=int(flags),
    )


def encode_disaster_batch(events: list["HazardEvent"]) -> bytes:
    """Encode multiple disasters to contiguous binary.

    Args:
        events: List of HazardEvent objects

    Returns:
        len(events) * 24 bytes
    """
    buffer = bytearray()
    for event in events:
        buffer.extend(encode_disaster(event))
    return bytes(buffer)


def decode_disaster_batch(
    data: bytes, count: int
) -> list[DisasterBinary]:
    """Decode contiguous binary to list of DisasterBinary.

    Args:
        data: count * 24 bytes
        count: Number of disasters to decode

    Returns:
        List of DisasterBinary objects
    """
    disasters = []
    for i in range(count):
        offset = i * 24
        disasters.append(decode_disaster(data[offset:offset + 24]))
    return disasters
