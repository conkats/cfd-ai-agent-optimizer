"""
Compare four bluff-body shapes (cylinder, square, half-cylinder, triangle)
from rigid-wall Code_Saturne runs in agent-orchestration-claude/case_<shape>/.

Outputs:
  results/shape_comparison.png

Usage:
  python3 plot_shape_comparison.py
"""

import os
import sys
import subprocess
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ── locations ────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR   = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
RESULTS    = os.path.join(ORCH_DIR, "results")
os.makedirs(RESULTS, exist_ok=True)

EXTRACT_SCRIPT = os.path.join(SCRIPT_DIR, "extract_wake_shape.py")

SALOME_ROOT = (
    "/home/katsa1k/apps/salome/"
    "SALOME-9.11.0-native-UB22.04-SRC/BINARIES-UB22.04"
)
SALOME_PVPYTHON = os.path.join(SALOME_ROOT, "ParaView", "bin", "pvpython")


# ── physical constants ──────────────────────────────────────────────────────

D    = 0.5      # characteristic dimension (m)
U    = 1.0      # reference velocity (m/s)
SPAN = 0.5      # extrusion in Y
RHO  = 1.0
NU   = 1.83e-5  # used for Reynolds number reporting

SHAPES = [
    dict(label="Cylinder",      key="cylinder",      color="C0"),
    dict(label="Square",        key="square",        color="C1"),
    dict(label="Half-Cylinder", key="half_cylinder", color="C2"),
    dict(label="Triangle",      key="triangle",      color="C3"),
]


# ── helpers ──────────────────────────────────────────────────────────────────

def find_latest_resu(case_dir):
    resu_root = os.path.join(case_dir, "RESU")
    if not os.path.isdir(resu_root):
        return None
    runs = sorted(d for d in os.listdir(resu_root)
                  if os.path.isdir(os.path.join(resu_root, d)))
    return os.path.join(resu_root, runs[-1]) if runs else None


def salome_ld_path():
    lib_dirs = []
    for root, dirs, _ in os.walk(SALOME_ROOT):
        if os.path.basename(root) == "lib":
            lib_dirs.append(root)
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    return ":".join(lib_dirs) + ((":" + existing) if existing else "")


def ensure_wake_profiles(resu_dir):
    out_prefix = os.path.join(resu_dir, "wake_profile")
    needed = [out_prefix + "_x5.csv", out_prefix + "_x8.csv"]
    if all(os.path.exists(p) for p in needed):
        return needed
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = salome_ld_path()
    print(f"  extracting wake profiles for {os.path.basename(resu_dir)} ...")
    subprocess.run(
        [SALOME_PVPYTHON, EXTRACT_SCRIPT, resu_dir, out_prefix],
        check=True, env=env,
    )
    return needed


def load_forces(resu_dir):
    path = os.path.join(resu_dir, "pressure_coefficient.csv")
    if not os.path.exists(path):
        return None, None, None
    data = np.genfromtxt(path, delimiter=",", skip_header=1)
    return data[:, 1], data[:, 2], data[:, 4]   # t, Fx, Fz


def steady_window(t):
    return t >= t[-1] / 2.0


def shedding_frequency(t, fz):
    zc = []
    for i in range(1, len(fz)):
        if fz[i-1] < 0 and fz[i] >= 0:
            frac = -fz[i-1] / (fz[i] - fz[i-1])
            zc.append(t[i-1] + frac * (t[i] - t[i-1]))
    if len(zc) < 2:
        return np.nan, 0
    periods = np.diff(zc)
    return 1.0 / periods.mean(), len(zc) - 1


def power_spectrum(t, x):
    n = len(x)
    if n < 2:
        return np.array([]), np.array([])
    dt = t[1] - t[0]
    f = np.fft.rfftfreq(n, dt)
    Y = np.abs(np.fft.rfft(x - x.mean())) / n
    return f, Y


# ── data gathering ───────────────────────────────────────────────────────────

def gather(shape):
    case_dir = os.path.join(ORCH_DIR, f"case_{shape['key']}")
    resu = find_latest_resu(case_dir)
    if resu is None:
        shape["status"] = "no RESU"
        return shape
    shape["resu"] = resu

    t, Fx, Fz = load_forces(resu)
    if t is None:
        shape["status"] = "no forces"
        return shape

    q_dyn = 0.5 * RHO * U**2 * D * SPAN
    Cd_t = Fx / q_dyn
    Cl_t = Fz / q_dyn

    mask = steady_window(t)
    Cd_ss = Cd_t[mask]
    Cl_ss = Cl_t[mask]
    Fz_ss = Fz[mask]
    t_ss  = t[mask]

    Cd_mean = Cd_ss.mean()
    Cd_std  = Cd_ss.std()
    Cl_rms  = np.sqrt(np.mean(Cl_ss**2))
    Cl_amp  = 0.5 * (Cl_ss.max() - Cl_ss.min())

    f_shed, n_cyc = shedding_frequency(t_ss, Fz_ss)
    St = f_shed * D / U if not np.isnan(f_shed) else np.nan
    Re = U * D / NU

    shape.update(dict(
        status="OK", t=t, Cd=Cd_t, Cl=Cl_t,
        Cd_mean=Cd_mean, Cd_std=Cd_std,
        Cl_rms=Cl_rms, Cl_amp=Cl_amp,
        f_shed=f_shed, St=St, Re=Re, n_cyc=n_cyc,
    ))
    return shape


# ── plotting ─────────────────────────────────────────────────────────────────

def plot_cd(ax, shapes):
    for s in shapes:
        if s.get("status") != "OK":
            continue
        ax.plot(s["t"], s["Cd"], lw=0.7, color=s["color"], label=s["label"])
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(r"$C_d$")
    ax.set_title("Drag coefficient $C_d(t)$")
    ax.grid(True, lw=0.4)
    ax.legend(fontsize=8)


def plot_cl(ax, shapes):
    for s in shapes:
        if s.get("status") != "OK":
            continue
        ax.plot(s["t"], s["Cl"], lw=0.7, color=s["color"], label=s["label"])
    ax.set_xlabel("Time (s)")
    ax.set_ylabel(r"$C_l$")
    ax.set_title("Lift coefficient $C_l(t)$")
    ax.grid(True, lw=0.4)
    ax.legend(fontsize=8)


def plot_spectrum(ax, shapes):
    for s in shapes:
        if s.get("status") != "OK":
            continue
        mask = steady_window(s["t"])
        f, Y = power_spectrum(s["t"][mask], s["Cl"][mask])
        St_axis = f * D / U
        sel = (St_axis > 1e-3) & (St_axis < 1.0)
        ax.semilogy(St_axis[sel], Y[sel], lw=0.9, color=s["color"],
                    label=f'{s["label"]} (St={s["St"]:.3f})')
        if not np.isnan(s["St"]):
            ax.axvline(s["St"], color=s["color"], lw=0.5, ls=":")
    ax.set_xlabel(r"Strouhal $St = fD/U$")
    ax.set_ylabel(r"$|\hat{C_l}|$")
    ax.set_title("Lift spectrum (steady-state window)")
    ax.set_xlim(0, 0.6)
    ax.grid(True, lw=0.4, which="both")
    ax.legend(fontsize=8)


def plot_bars(ax, shapes):
    ok = [s for s in shapes if s.get("status") == "OK"]
    labels = [s["label"]   for s in ok]
    cd     = [s["Cd_mean"] for s in ok]
    cls    = [s["Cl_rms"]  for s in ok]
    st     = [s["St"]      for s in ok]
    colors = [s["color"]   for s in ok]
    x = np.arange(len(labels))
    w = 0.27
    ax.bar(x - w, cd,  w, color=colors, alpha=0.85,
           edgecolor="k", lw=0.4, label=r"$\bar{C_d}$")
    ax.bar(x,     cls, w, color=colors, alpha=0.55,
           edgecolor="k", lw=0.4, label=r"$C_{l,rms}$", hatch="///")
    ax.bar(x + w, st,  w, color=colors, alpha=0.30,
           edgecolor="k", lw=0.4, label=r"$St$", hatch="xxx")
    for i, (a, b, c) in enumerate(zip(cd, cls, st)):
        ax.text(i - w, a, f"{a:.2f}", ha="center", va="bottom", fontsize=7)
        ax.text(i,     b, f"{b:.2f}", ha="center", va="bottom", fontsize=7)
        ax.text(i + w, c, f"{c:.2f}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=12)
    ax.set_title("Integral quantities by shape")
    ax.grid(True, axis="y", lw=0.4)
    ax.legend(fontsize=8, loc="upper left")


def plot_wake(ax, shapes, station, component):
    col = 1 if component == "Vx" else 2
    for s in shapes:
        if s.get("status") != "OK":
            continue
        csv_path = os.path.join(s["resu"], f"wake_profile_{station}.csv")
        if not os.path.exists(csv_path):
            continue
        data = np.genfromtxt(csv_path, delimiter=",", skip_header=1)
        z, v = data[:, 0], data[:, col]
        ax.plot(v / U, z / D, lw=1.0, color=s["color"], label=s["label"])
    ax.axhline(0, lw=0.5, color="k", ls="--")
    ax.axvline(0, lw=0.5, color="k", ls="--")
    ax.set_xlabel(f"${component[0]}_{component[1].lower()} / U$")
    ax.set_ylabel("$z / D$")
    direction = "streamwise" if component == "Vx" else "cross-flow"
    ax.set_title(f"Wake {direction} velocity at {station}")
    ax.grid(True, lw=0.4)
    ax.legend(fontsize=8)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    print("Gathering data for 4 shapes ...")
    for s in SHAPES:
        gather(s)

    print("\nGenerating wake profiles (pvpython) where missing ...")
    for s in SHAPES:
        if s.get("status") == "OK":
            ensure_wake_profiles(s["resu"])

    fmt = "{:<14s} {:>8s} {:>10s} {:>10s} {:>10s} {:>10s} {:>8s} {:>6s}"
    print("\n" + "=" * 92)
    print(fmt.format("Shape", "Status", "Cd_mean", "Cd_std",
                     "Cl_rms", "Cl_amp", "St", "Ncyc"))
    print("-" * 92)
    for s in SHAPES:
        if s.get("status") != "OK":
            print(f"{s['label']:<14s} {s.get('status','??'):>8s}")
            continue
        print("{:<14s} {:>8s} {:>10.3f} {:>10.3f} {:>10.3f} {:>10.3f} {:>8.3f} {:>6d}"
              .format(s["label"], s["status"], s["Cd_mean"], s["Cd_std"],
                      s["Cl_rms"], s["Cl_amp"], s["St"], s["n_cyc"]))
    print("=" * 92)

    fig, axes = plt.subplots(3, 2, figsize=(13, 13))
    fig.suptitle("2D bluff-body shape comparison (rigid wall, Code_Saturne)",
                 fontsize=13, y=0.995)

    plot_cd(      axes[0, 0], SHAPES)
    plot_cl(      axes[0, 1], SHAPES)
    plot_spectrum(axes[1, 0], SHAPES)
    plot_bars(    axes[1, 1], SHAPES)
    plot_wake(    axes[2, 0], SHAPES, "x5", "Vx")
    plot_wake(    axes[2, 1], SHAPES, "x8", "Vz")

    plt.tight_layout(rect=[0, 0, 1, 0.985])
    out = os.path.join(RESULTS, "shape_comparison.png")
    plt.savefig(out, dpi=140)
    print(f"\nFigure saved: {out}")


if __name__ == "__main__":
    main()
