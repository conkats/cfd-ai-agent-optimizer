"""
Combine the four per-shape velocity-magnitude contour PNGs into one 2x2 figure.

Usage:
  python3 combine_contours.py
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR   = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
RESULTS    = os.path.join(ORCH_DIR, "results")

SHAPES = [
    ("cylinder",      "Cylinder"),
    ("square",        "Square"),
    ("half_cylinder", "Half-Cylinder"),
    ("triangle",      "Triangle"),
]


def main():
    fig, axes = plt.subplots(2, 2, figsize=(16, 9))
    fig.suptitle("Velocity magnitude (m/s) at y=0.25 m, t = t_end "
                 "— common range 0–1.5 m/s",
                 fontsize=14, y=0.995)

    for ax, (key, label) in zip(axes.flat, SHAPES):
        png = os.path.join(RESULTS, f"contour_{key}.png")
        if not os.path.exists(png):
            ax.text(0.5, 0.5, f"Missing:\n{png}",
                    ha="center", va="center", transform=ax.transAxes)
            ax.set_title(label)
            ax.set_xticks([]); ax.set_yticks([])
            continue
        img = mpimg.imread(png)
        ax.imshow(img)
        ax.set_title(label, fontsize=12)
        ax.set_xticks([]); ax.set_yticks([])

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out = os.path.join(RESULTS, "contours_2x2.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Combined figure saved: {out}")


if __name__ == "__main__":
    main()
