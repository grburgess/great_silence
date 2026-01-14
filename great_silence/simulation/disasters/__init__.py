"""Disaster management infrastructure for galactic simulation.

This module provides high-performance tools for tracking, storing, and
retrieving astrophysical disaster events (supernovae, GRBs, NSMs) using
binary encoding, spatial indexing, and tiered storage.
"""

from .encoding import (
    DisasterBinary,
    encode_disaster,
    decode_disaster,
    encode_disaster_batch,
    decode_disaster_batch,
    DISASTER_BINARY_FORMAT,
    EVENT_TYPE_MAP,
    EVENT_TYPE_REVERSE,
)
from .spatial_index import DisasterSpatialIndex
from .recovery import SterilizationStatus, RecoveryQueue
from .scheduler import SupernovaScheduler
from .archiver import DisasterArchiver
from .unified_scheduler import (
    UnifiedDisasterScheduler,
    DisasterType,
    ScheduledDisaster,
)

__all__ = [
    "DisasterBinary",
    "encode_disaster",
    "decode_disaster",
    "encode_disaster_batch",
    "decode_disaster_batch",
    "DISASTER_BINARY_FORMAT",
    "EVENT_TYPE_MAP",
    "EVENT_TYPE_REVERSE",
    "DisasterSpatialIndex",
    "SterilizationStatus",
    "RecoveryQueue",
    "SupernovaScheduler",
    "DisasterArchiver",
    "UnifiedDisasterScheduler",
    "DisasterType",
    "ScheduledDisaster",
]
