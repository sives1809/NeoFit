"""
visualization.py
----------------
Load the saved CSV and plot growth trends over time for arm, shoulder,
and thigh measurements (and pseudo-3D areas).

Run directly:
    python visualization.py
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

DEFAULT_CSV_PATH = os.path.join(os.path.dirname(__file__), "data",
                                "measurements.csv")


def load_data(path: str = DEFAULT_CSV_PATH) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No measurements CSV found at {path}. "
            "Capture some sessions with main.py first."
        )
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def plot_growth(df: pd.DataFrame) -> None:
    if df.empty:
        print("CSV is empty — capture at least one session before plotting.")
        return

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)

    # --- Lengths / widths in cm ---
    ax1 = axes[0]
    ax1.plot(df["timestamp"], df["arm_cm"], marker="o", label="Arm length (cm)")
    ax1.plot(df["timestamp"], df["shoulder_cm"], marker="s",
             label="Shoulder width (cm)")
    ax1.plot(df["timestamp"], df["thigh_cm"], marker="^",
             label="Thigh length (cm)")
    ax1.set_ylabel("Centimeters")
    ax1.set_title("Body measurements over time")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # --- Pseudo-3D areas ---
    ax2 = axes[1]
    ax2.plot(df["timestamp"], df["arm_area"], marker="o",
             label="Arm pseudo-3D area (cm^2)")
    ax2.plot(df["timestamp"], df["thigh_area"], marker="^",
             label="Thigh pseudo-3D area (cm^2)")
    ax2.set_ylabel("Area (cm^2)")
    ax2.set_xlabel("Session timestamp")
    ax2.set_title("Pseudo-3D muscle size over time")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    fig.autofmt_xdate()
    plt.tight_layout()
    plt.show()


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV_PATH
    try:
        df = load_data(path)
    except FileNotFoundError as e:
        print(e)
        return 1
    plot_growth(df)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
