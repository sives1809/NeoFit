"""
storage.py
----------
Append-only CSV storage for measurement sessions.

Schema:
    timestamp, arm_cm, shoulder_cm, thigh_cm, arm_area, thigh_area
"""

import csv
import os
from datetime import datetime
from typing import Optional

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "data",
                                "measurements.csv")

FIELDNAMES = [
    "timestamp",
    "arm_cm",
    "shoulder_cm",
    "thigh_cm",
    "arm_area",
    "thigh_area",
]


def _ensure_file(path: str) -> None:
    """Create the CSV (with header) and parent dir if they don't exist."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def save_measurement(front_cm: dict,
                     pseudo3d: dict,
                     path: Optional[str] = None) -> str:
    """
    Append one row to the measurements CSV. Front-view cm values are used
    for the per-region length columns; pseudo-3D areas come from the
    combined front+side computation.

    Returns the path written to.
    """
    path = path or DEFAULT_CSV_PATH
    _ensure_file(path)

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "arm_cm": round(front_cm.get("arm_cm", 0.0), 2),
        "shoulder_cm": round(front_cm.get("shoulder_cm", 0.0), 2),
        "thigh_cm": round(front_cm.get("thigh_cm", 0.0), 2),
        "arm_area": round(pseudo3d.get("arm_area", 0.0), 2),
        "thigh_area": round(pseudo3d.get("thigh_area", 0.0), 2),
    }

    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)

    return path
