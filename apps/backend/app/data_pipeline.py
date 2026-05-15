from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class DataSnapshot:
    snapshot_id: str
    layer: str
    created_at: datetime
    source_dataset: str
    schema_version: str
    record_count: int
    metadata: dict[str, Any]


def build_lineage_record(
    *,
    snapshot_id: str,
    layer: str,
    source_dataset: str,
    schema_version: str,
    record_count: int,
    metadata: dict[str, Any] | None = None,
) -> DataSnapshot:
    return DataSnapshot(
        snapshot_id=snapshot_id,
        layer=layer,
        created_at=datetime.now(tz=UTC),
        source_dataset=source_dataset,
        schema_version=schema_version,
        record_count=record_count,
        metadata=metadata or {},
    )


def quality_checks(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "row_count": 0,
            "missingness_ratio": 1.0,
            "timestamp_anomaly_ratio": 0.0,
            "bot_suspect_ratio": 0.0,
            "timezone_confidence": "low",
        }

    total_fields = sum(len(r) for r in rows)
    missing_fields = sum(1 for row in rows for value in row.values() if value in (None, "", []))
    ts_fields = [row.get("timestamp_utc") for row in rows]
    timestamp_anomalies = sum(1 for ts in ts_fields if isinstance(ts, str) and ts.endswith("00:00:00Z"))
    bot_suspects = sum(1 for row in rows if str(row.get("actor", "")).endswith("[bot]"))
    timezone_confidence = "high" if timestamp_anomalies / len(rows) < 0.1 else "low"
    return {
        "row_count": len(rows),
        "missingness_ratio": round(missing_fields / max(1, total_fields), 4),
        "timestamp_anomaly_ratio": round(timestamp_anomalies / len(rows), 4),
        "bot_suspect_ratio": round(bot_suspects / len(rows), 4),
        "timezone_confidence": timezone_confidence,
    }
