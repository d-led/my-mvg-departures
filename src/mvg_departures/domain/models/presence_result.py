"""Presence tracking result domain model."""

from pydantic import BaseModel, ConfigDict


class PresenceResult(BaseModel):
    """Result of a presence tracking operation.

    Contains user ID and updated presence counts.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str
    local_count: int
    total_count: int


class PresenceCounts(BaseModel):
    """Presence counts for a dashboard."""

    model_config = ConfigDict(frozen=True)

    local_count: int
    total_count: int


class PresenceSyncResult(BaseModel):
    """Result of a presence synchronization operation.

    Contains counts of users added and removed during sync.
    """

    model_config = ConfigDict(frozen=True)

    added_count: int
    removed_count: int
