# AI Muscle Growth Tracker

A CPU-only, fully local Python system that uses **MediaPipe Pose** + **OpenCV**
to measure body regions from a webcam, scales pixels to centimeters using your
real height, approximates muscle size with a pseudo-3D ellipse model from
front + side views, stores sessions in CSV, and visualizes growth over time
with **matplotlib**.

Built as a final-year engineering project — focus is on geometric modeling,
stability, and clear modular code, not deep learning.

---

## Project structure

```
muscle_growth_tracker/
├── main.py            # Camera loop, UI overlay, key handling
├── measurement.py     # Distance calculations between pose landmarks
├── scaling.py         # Pixel -> cm conversion using user height
├── pseudo3d.py        # Ellipse area: pi * width * thickness / 4
├── storage.py         # Append-only CSV
├── visualization.py   # Matplotlib growth charts
├── data/
│   └── measurements.csv  (auto-created on first save)
├── requirements.txt
└── README.md
```

---

## Setup

Requires **Python 3.9–3.11** (MediaPipe does not yet support 3.12+ on all
platforms).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

---

## Run

### 1. Live tracker

```bash
python main.py
```

You'll be asked for your height in cm, then the webcam window opens.

**Key bindings**

| Key | Action |
|-----|--------|
| `M` | Toggle capture **mode** (FRONT ↔ SIDE) — applies the right pose validation |
| `F` | Capture **Front** view (widths) — only allowed in FRONT mode |
| `S` | Capture **Side** view (thicknesses) — only allowed in SIDE mode |
| `C` | Combine F+S into pseudo-3D area and **save** to CSV |
| `V` | Open growth charts |
| `Q` | Quit |

Workflow per session:

1. Start in FRONT mode. Stand square to the camera, full body in frame.
2. When arm/shoulder/thigh values look stable, press **F**. Mode auto-switches to SIDE.
3. Turn 90° sideways (shoulders stacked); when status reads READY, press **S**.
4. Press **C** to save the row.

Pose validation rules:
- **FRONT** rejects if shoulders are tilted more than ±12° from horizontal.
- **SIDE** rejects if the shoulders are not nearly stacked along the vertical axis (|left.x − right.x| / nose-to-ankle ≤ 0.08).

### 2. Growth charts

```bash
python visualization.py
```

Reads `data/measurements.csv` and plots length and pseudo-3D area trends.

---

## How it works

- **Pose detection** — MediaPipe Pose (`model_complexity=1`) returns 33 body
  landmarks per frame.
- **Measurements** — Euclidean distance in pixels between landmark pairs
  (shoulder↔elbow, shoulder↔shoulder, hip↔knee).
- **Real-world scale** — `nose ↔ midpoint(ankles)` pixel distance is assumed
  to equal `0.93 × user_height_cm`. This gives a `cm/px` factor used for every
  measurement.
- **Stability** — Last 12 frames are kept in a rolling buffer; the displayed
  value is the **median** per measurement. Frames where the shoulder line is
  tilted more than ~12° from horizontal are rejected.
- **Pseudo-3D** — Front view supplies the **width**, side view supplies the
  **thickness**, area ≈ `π · width · thickness / 4`. This is a geometric
  proxy for muscle cross-section, suitable for tracking *relative* growth.
- **Storage** — Append-only CSV with timestamp + cm values + areas.

---

## Implemented features

- Real-time MediaPipe Pose detection with skeleton overlay
- Arm length, shoulder width, thigh length measurement
- Pixel→cm scaling using user height
- Multi-frame median smoothing + tilt rejection
- Front + side multi-view capture
- Pseudo-3D ellipse muscle area (arm, thigh)
- CSV persistence with timestamps
- Matplotlib growth visualization

## Future scope

- True 3D reconstruction from multiple synchronized cameras
- Body fat / circumference estimation via segmentation masks
- Mobile capture (Android / iOS) with on-device MediaPipe
- Per-side (left vs right) asymmetry tracking
- Auto-detection of front vs side orientation (no manual F/S keys)
- Cloud sync and multi-user profiles

---

## Troubleshooting

- **Webcam doesn't open** — change `cv2.VideoCapture(0)` to `1` or `2` in
  `main.py` if you have multiple cameras.
- **MediaPipe install fails** — ensure Python is 3.9–3.11 and pip is recent
  (`pip install -U pip`).
- **Values look off** — make sure your full body (nose to ankles) is visible
  and you're standing upright; the scale depends on the nose↔ankle reference.
- **"Reject: square up to camera"** — your shoulders are tilted; face the
  camera straight on.
