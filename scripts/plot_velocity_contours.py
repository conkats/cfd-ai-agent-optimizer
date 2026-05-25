"""
Render a velocity-magnitude contour (y=0.25 slice, last time step) for each
shape and save individual PNGs.

Run under SALOME pvpython:
  pvpython plot_velocity_contours.py [<results_dir>]

Outputs:
  results/contour_<shape>.png  for each shape that has a RESU

The companion script combine_contours.py assembles these into a 2x2 figure.
"""

import sys
import os
import paraview.simple as pv


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ORCH_DIR   = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

SHAPES = ["cylinder", "square", "half_cylinder", "triangle"]

# Common contour range across all shapes (per research brief)
VMIN, VMAX = 0.0, 1.5


def find_latest_resu(case_dir):
    resu_root = os.path.join(case_dir, "RESU")
    if not os.path.isdir(resu_root):
        return None
    runs = sorted(d for d in os.listdir(resu_root)
                  if os.path.isdir(os.path.join(resu_root, d)))
    return os.path.join(resu_root, runs[-1]) if runs else None


def render_one(shape, out_dir):
    case_dir = os.path.join(ORCH_DIR, f"case_{shape}")
    resu = find_latest_resu(case_dir)
    if resu is None:
        print(f"[{shape}] no RESU; skip")
        return False
    case_file = os.path.join(resu, "postprocessing",
                             "RESULTS_FLUID_DOMAIN.case")
    if not os.path.exists(case_file):
        print(f"[{shape}] no EnSight case file at {case_file}; skip")
        return False

    print(f"[{shape}] loading {case_file}")
    reader = pv.EnSightReader(
        registrationName=f"{shape}_fluid", CaseFileName=case_file)
    reader.CellArrays = ["Velocity"]
    reader.UpdatePipeline()

    times = list(pv.GetTimeKeeper().TimestepValues)
    last_t = times[-1]
    print(f"[{shape}] last time = {last_t:.3f}")

    c2p = pv.CellDatatoPointData(
        registrationName=f"{shape}_c2p", Input=reader)
    c2p.ProcessAllArrays = 1

    slice_ = pv.Slice(registrationName=f"{shape}_slice", Input=c2p)
    slice_.SliceType = "Plane"
    slice_.SliceType.Origin = [5.0, 0.25, 0.0]
    slice_.SliceType.Normal = [0.0, 1.0, 0.0]

    calc = pv.Calculator(registrationName=f"{shape}_mag", Input=slice_)
    calc.ResultArrayName = "Umag"
    calc.Function = "mag(Velocity)"

    # Render view
    view = pv.CreateView("RenderView")
    view.ViewSize = [1200, 700]
    view.OrientationAxesVisibility = 0
    view.CameraParallelProjection = 1
    view.Background = [1.0, 1.0, 1.0]

    disp = pv.Show(calc, view)
    disp.Representation = "Surface"
    pv.ColorBy(disp, ("POINTS", "Umag"))

    lut = pv.GetColorTransferFunction("Umag")
    lut.ApplyPreset("Viridis (matplotlib)", True)
    lut.RescaleTransferFunction(VMIN, VMAX)
    lut.NumberOfTableValues = 256

    disp.SetScalarBarVisibility(view, True)
    sb = pv.GetScalarBar(lut, view)
    sb.Title = "|U| (m/s)"
    sb.ComponentTitle = ""
    sb.WindowLocation = "Lower Right Corner"

    pv.UpdatePipeline(time=last_t, proxy=calc)

    # Camera: look down +Y onto the y=0.25 slice. Flow X is horizontal
    # (image right), cross-flow Z is vertical (image up).
    # ViewUp=Z makes Z point up; the right-hand X axis ends up pointing right.
    # But ParaView's RenderView default has +X to the right of the screen when
    # the camera looks down -Y, so we set CameraPosition above the plane and
    # ViewUp=+Z. With CameraPosition.y > focal.y, camera looks in -Y direction.
    view.CameraPosition         = [5.0, -10.0, 0.0]
    view.CameraFocalPoint       = [5.0, 0.25, 0.0]
    view.CameraViewUp           = [0.0, 0.0, 1.0]
    view.CameraParallelScale    = 2.7

    out_png = os.path.join(out_dir, f"contour_{shape}.png")
    pv.SaveScreenshot(out_png, view, ImageResolution=[1200, 700],
                      OverrideColorPalette="WhiteBackground")
    print(f"[{shape}] saved {out_png}")

    pv.Delete(disp)
    pv.Delete(calc)
    pv.Delete(slice_)
    pv.Delete(c2p)
    pv.Delete(reader)
    pv.Delete(view)
    return True


def main():
    out_dir = os.path.join(ORCH_DIR, "results")
    os.makedirs(out_dir, exist_ok=True)
    for shape in SHAPES:
        try:
            render_one(shape, out_dir)
        except Exception as e:
            print(f"[{shape}] ERROR: {e}")


if __name__ == "__main__":
    main()
