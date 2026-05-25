"""
Extract wake velocity profiles at x=5 m and x=8 m for a Code_Saturne RESU.

Usage (under pvpython):
  pvpython extract_wake_shape.py <RESU_dir> <output_prefix>

Outputs:
  <prefix>_x5.csv  - wake at x=5 m (downstream of obstacle at x=2.5)
  <prefix>_x8.csv  - wake at x=8 m (mid wake)

CSV header: z,Vx,Vz
"""

import sys
import os
import numpy as np
import paraview.simple as pv
from paraview.vtk.numpy_interface import dataset_adapter as dsa


def main():
    if len(sys.argv) < 3:
        print("Usage: pvpython extract_wake_shape.py <RESU_dir> <output_prefix>")
        sys.exit(1)

    resu_dir  = sys.argv[1]
    prefix    = sys.argv[2]
    case_file = os.path.join(resu_dir, "postprocessing", "RESULTS_FLUID_DOMAIN.case")

    if not os.path.exists(case_file):
        print("ERROR: cannot find", case_file)
        sys.exit(1)

    reader = pv.EnSightReader(registrationName="fluid", CaseFileName=case_file)
    reader.CellArrays = ["Velocity"]
    reader.UpdatePipeline()

    times = list(pv.GetTimeKeeper().TimestepValues)
    last_t = times[-1]
    print("Total time steps: %d, extracting at t = %.4f s" % (len(times), last_t))

    c2p = pv.CellDatatoPointData(registrationName="c2p", Input=reader)
    c2p.ProcessAllArrays = 1

    y_mid        = 0.25
    z_min, z_max = -2.5, 2.5
    n_pts        = 201

    for x_st, tag in [(5.0, "x5"), (8.0, "x8")]:
        line = pv.PlotOverLine(registrationName="line_" + tag, Input=c2p)
        line.Point1     = [x_st, y_mid, z_min]
        line.Point2     = [x_st, y_mid, z_max]
        line.Resolution = n_pts - 1

        pv.UpdatePipeline(time=last_t, proxy=line)
        raw     = pv.servermanager.Fetch(line)
        wrapped = dsa.WrapDataObject(raw)

        n      = raw.GetNumberOfPoints()
        pts    = np.array([raw.GetPoint(i) for i in range(n)])
        z_arr  = pts[:, 2]

        vel = wrapped.PointData["Velocity"]
        if hasattr(vel, "Arrays"):
            vel = vel.Arrays[0]
        vel = np.asarray(vel)

        vx_arr = vel[:, 0]
        vz_arr = vel[:, 2]

        idx = np.argsort(z_arr)
        out = prefix + "_" + tag + ".csv"
        with open(out, "w") as f:
            f.write("z,Vx,Vz\n")
            for i in idx:
                f.write("%.8e,%.8e,%.8e\n" % (z_arr[i], vx_arr[i], vz_arr[i]))

        print("Written %s (%d pts, x=%.1f, t=%.2f s)" % (out, n, x_st, last_t))
        pv.Delete(line)

    pv.Delete(c2p)
    pv.Delete(reader)


if __name__ == "__main__":
    main()
