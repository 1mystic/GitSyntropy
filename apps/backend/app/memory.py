from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal


MemoryTier = Literal["short", "session", "knowledge"]


@dataclass(slots=True)
class MemoryEntry:
    key: str
    value: dict[str, Any]
    tier: MemoryTier
    provenance: str
    created_at: datetime
    expires_at: datetime | None


class MemoryManager:
    """Simple in-process memory tiers with TTL + provenance metadata."""

    def __init__(self) -> None:
        self._store: dict[MemoryTier, dict[str, list[MemoryEntry]]] = {
            "short": defaultdict(list),
            "session": defaultdict(list),
            "knowledge": defaultdict(list),
        }

    def put(
        self,
        *,
        tier: MemoryTier,
        key: str,
        value: dict[str, Any],
        provenance: str,
        ttl_seconds: int | None,
    ) -> None:
        now = datetime.now(tz=UTC)
        expires_at = now + timedelta(seconds=ttl_seconds) if ttl_seconds else None
        self._store[tier][key].append(
            MemoryEntry(
                key=key,
                value=value,
                tier=tier,
                provenance=provenance,
                created_at=now,
                expires_at=expires_at,
            )
        )
        self.cleanup()

    def recent(self, *, tier: MemoryTier, key: str, limit: int = 10) -> list[MemoryEntry]:
        self.cleanup()
        return self._store[tier].get(key, [])[-limit:]

    def cleanup(self) -> None:
        now = datetime.now(tz=UTC)
        for tier, bucket in self._store.items():
            for key in list(bucket.keys()):
                bucket[key] = [
                    entry
                    for entry in bucket[key]
                    if entry.expires_at is None or entry.expires_at > now
                ]
                if not bucket[key]:
                    del bucket[key]

