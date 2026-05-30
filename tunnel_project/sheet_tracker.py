"""sheet_tracker.py - Deformation monitoring campaign tracker.

Headless, dependency-light record of per-campaign tunnel deformation metrics
with alert classification. Stores one row per monitoring campaign (T0, T1, ...)
in a CSV log so settlement/convergence trends can be followed over time and
pushed to Google Sheets (see tunnel_tracker.gs).

Pure standard library (csv, json, datetime, dataclasses); no Qt/GUI import, so
it runs in batch jobs and CI. NumPy is used only if present, for convenience.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Alert thresholds (mm / percent) mirror tunnel_analysis.exporter.TunnelExporter
# so the tracker and the report classify deformation identically.
THRESHOLDS: Dict[str, Dict[str, float]] = {
    "crown_settlement_mm":    {"caution": 10.0, "critical": 25.0},
    "lateral_convergence_mm": {"caution": 15.0, "critical": 30.0},
    "ovality_mean_pct":       {"caution":  0.5, "critical":  1.0},
    "eccentricity_mean_mm":   {"caution": 10.0, "critical": 25.0},
}

# Metrics tracked per campaign, in stable column order.
METRIC_KEYS: Tuple[str, ...] = (
    "crown_settlement_mm",
    "lateral_convergence_mm",
    "ovality_mean_pct",
    "eccentricity_mean_mm",
)

_STATUS_RANK = {"ok": 0, "n/a": 0, "caution": 1, "critical": 2}


def classify(metric_key: str, value: Optional[float]) -> str:
    """Return alert level ("ok"/"caution"/"critical"/"n/a") for a metric value."""
    thr = THRESHOLDS.get(metric_key)
    if thr is None or value is None or not math.isfinite(value):
        return "n/a"
    if abs(value) >= thr["critical"]:
        return "critical"
    if abs(value) >= thr["caution"]:
        return "caution"
    return "ok"


def worst_status(statuses: List[str]) -> str:
    """Return the most severe status from a list."""
    if not statuses:
        return "n/a"
    return max(statuses, key=lambda s: _STATUS_RANK.get(s, 0))


@dataclass
class CampaignRecord:
    """A single monitoring campaign's deformation metrics and alert state."""
    label: str
    timestamp: str
    metrics: Dict[str, float] = field(default_factory=dict)

    @property
    def statuses(self) -> Dict[str, str]:
        return {k: classify(k, self.metrics.get(k)) for k in METRIC_KEYS}

    @property
    def overall_status(self) -> str:
        return worst_status(list(self.statuses.values()))

    def to_row(self) -> Dict[str, str]:
        row: Dict[str, str] = {"label": self.label, "timestamp": self.timestamp}
        for key in METRIC_KEYS:
            val = self.metrics.get(key)
            row[key] = "" if val is None or not math.isfinite(val) else f"{val:.4f}"
            row[f"{key}_status"] = classify(key, val)
        row["overall_status"] = self.overall_status
        return row


def _csv_fieldnames() -> List[str]:
    names = ["label", "timestamp"]
    for key in METRIC_KEYS:
        names.append(key)
        names.append(f"{key}_status")
    names.append("overall_status")
    return names


class MonitoringTracker:
    """CSV-backed append log of deformation monitoring campaigns."""

    def __init__(self, csv_path: str) -> None:
        self.path = Path(csv_path)

    def record_campaign(
        self,
        label: str,
        metrics: Dict[str, float],
        timestamp: Optional[str] = None,
    ) -> CampaignRecord:
        """Append a campaign row and return its classified record."""
        if not label:
            raise ValueError("Campaign label must be non-empty.")
        ts = timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        clean = {k: float(metrics[k]) for k in METRIC_KEYS if k in metrics and metrics[k] is not None}
        record = CampaignRecord(label=label, timestamp=ts, metrics=clean)
        self._append(record)
        return record

    def _append(self, record: CampaignRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        is_new = not self.path.exists() or self.path.stat().st_size == 0
        with open(self.path, "a", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=_csv_fieldnames())
            if is_new:
                writer.writeheader()
            writer.writerow(record.to_row())

    def load(self) -> List[CampaignRecord]:
        """Read all recorded campaigns from the CSV log."""
        if not self.path.exists():
            return []
        records: List[CampaignRecord] = []
        with open(self.path, "r", newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                metrics: Dict[str, float] = {}
                for key in METRIC_KEYS:
                    raw = (row.get(key) or "").strip()
                    if raw:
                        try:
                            metrics[key] = float(raw)
                        except ValueError:
                            pass
                records.append(CampaignRecord(
                    label=row.get("label", ""),
                    timestamp=row.get("timestamp", ""),
                    metrics=metrics,
                ))
        return records

    def latest(self) -> Optional[CampaignRecord]:
        records = self.load()
        return records[-1] if records else None

    def trend(self, metric_key: str) -> List[Tuple[str, float]]:
        """Return [(label, value), ...] for a metric across all campaigns."""
        if metric_key not in METRIC_KEYS:
            raise KeyError(f"Unknown metric '{metric_key}'. Choose from {METRIC_KEYS}.")
        out: List[Tuple[str, float]] = []
        for rec in self.load():
            val = rec.metrics.get(metric_key)
            if val is not None and math.isfinite(val):
                out.append((rec.label, val))
        return out


def push_to_sheets(
    record: "CampaignRecord",
    web_app_url: str,
    secret: Optional[str] = None,
    timeout: float = 15.0,
) -> Dict[str, object]:
    """POST a campaign record to the tunnel_tracker.gs web app (Google Sheets).

    Uses only the standard library so it stays importable in headless/batch
    contexts. Network access is required only when this function is called.
    """
    import json as _json
    import urllib.request

    campaign = record.to_row()
    body: Dict[str, object] = {"campaign": campaign}
    if secret:
        body["secret"] = secret
    data = _json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        web_app_url, data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    try:
        return _json.loads(raw)
    except ValueError:
        return {"ok": False, "error": "Non-JSON response", "raw": raw}


def metrics_from_parameters(parameters: Dict[str, float]) -> Dict[str, float]:
    """Extract tracked metrics from a PipelineContext.parameters dict.

    Accepts the aggregate keys produced by tunnel_analysis.parameters
    (crown_settlement_mm, lateral_convergence_mm, ovality_mean_pct,
    eccentricity_mean_mm) and ignores anything else.
    """
    out: Dict[str, float] = {}
    for key in METRIC_KEYS:
        val = parameters.get(key)
        if isinstance(val, (int, float)) and math.isfinite(float(val)):
            out[key] = float(val)
    return out
