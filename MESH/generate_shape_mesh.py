"""
Generate 2D cross-flow bluff-body mesh for Code_Saturne shape-comparison study.

Uses the gmsh Python API with the OpenCASCADE (OCC) kernel:
  1. Build a 2D fluid surface in the X-Z plane (Y=0) by boolean-cutting the
     obstacle from the domain rectangle. All geometry is built with explicit
     3D points at Y=0 so the plane is X-Z, not OCC's default X-Y.
  2. Extrude the 2D surface in +Y to produce a single 3D hex/prism layer.
  3. Apply Distance+Threshold mesh-size fields for near-obstacle refinement.
  4. Identify physical surface groups by bounding-box queries.
  5. Write Gmsh v2.2 ASCII format.

Geometry (all dimensions in metres, SI):
  - Flow direction : X  (inlet at x=0, outlet at x=10)
  - Cross-flow     : Z  (z in [-2.5, 2.5])
  - Extrusion      : Y  (y in [0, 0.5], quasi-2D, 1 element thick)
  - Obstacle centre: (x=2.5, z=0), characteristic dimension D = 0.5 m
  - 5D from inlet, 15D to outlet

Shape orientations (--shape flag):
  cylinder:
    Circle of diameter D = 0.5 m centred at (2.5, 0, 0).
    Built from four 90-degree arcs in the X-Z plane at Y=0.

  square:
    Axis-aligned square, side D = 0.5 m, centred at (2.5, 0, 0).
    Corners at x=2.25/2.75, z=+/-0.25.

  half_cylinder:
    Semicircle (D-shape), diameter D = 0.5 m.
    Flat face UPSTREAM at x = 2.5 (spanning z in [-0.25, +0.25]).
    Curved surface bulging DOWNSTREAM from x=2.5 to x=3.0.
    Physically: the upstream flat face forces immediate flow separation
    like a blunt body; the curved downstream half reduces the base-pressure
    deficit relative to a full square or blunt plate.

  triangle:
    Equilateral triangle, side D = 0.5 m.
    Apex pointing UPSTREAM (into flow, at minimum X).
    Flat base perpendicular to flow at downstream side.
    Centroid at (2.5, 0, 0).
    h = D*sqrt(3)/2 ≈ 0.4330 m (height along X).
    Apex:  x = 2.5 - 2h/3 ≈ 2.211, z = 0
    Base:  x = 2.5 + h/3  ≈ 2.644, z = +/-0.25

Physical surface tags (must match setup.xml boundary condition selectors):
  1 = inlet     (x = 0 face)
  2 = outlet    (x = Lx = 10 face)
  3 = cylindre  (obstacle wall — name kept for setup.xml compatibility)
  4 = symmetry  (y = 0 and y = 0.5 extrusion faces)
  5 = updown    (z = +/-2.5 cross-flow walls)
 10 = fluid     (3D volume — required by Code_Saturne as a zone)

Code_Saturne integration notes:
  - Output format: Gmsh v2.2 ASCII (.msh). Place file in the MESH/ directory.
  - The 'cylindre' Physical Surface matches the ALE internal-coupling BC
    selector in setup.xml. It contains all extruded sides of the obstacle
    perimeter as a single group.
  - k-omega SST wall-function (type 3) at Re ≈ 33000 (D=0.5, U=1, nu=1.5e-5):
    target first-cell height y1 ≈ D/300 ≈ 1.7e-3 m (y+ ≈ 30-100).
    With raf=2, near_size = 0.025 m. Use raf=4 for y+ compliance.
  - Square, half-cylinder, and triangle shapes produce quad-dominant meshes
    with some triangular faces that extrude as prism (wedge) elements.
    Prism elements are valid in Code_Saturne.

Usage:
  python generate_shape_mesh.py --shape cylinder
  python generate_shape_mesh.py --shape square       --raf 4
  python generate_shape_mesh.py --shape half_cylinder --out half_cylinder.msh
  python generate_shape_mesh.py --shape triangle     --raf 2 --out tri.msh
"""

import gmsh
import math
import os
import sys
import argparse
from typing import List


# ---------------------------------------------------------------------------
# Domain / obstacle parameters (all in metres)
# ---------------------------------------------------------------------------
LX = 10.0    # domain length in X  [0, LX]
LZ = 5.0     # domain height in Z  [-LZ/2, LZ/2]
LY = 0.5     # extrusion depth in Y  [0, LY]  (one hex layer)
OX = 2.5     # obstacle centre X
OZ = 0.0     # obstacle centre Z (at Z=0)
D  = 0.5     # obstacle characteristic dimension
R  = D / 2   # = 0.25 m


# ---------------------------------------------------------------------------
# Obstacle surface builders
# All geometry in the X-Z plane at Y=0.
# Each function returns the surface tag of the obstacle 2D surface.
# ---------------------------------------------------------------------------

def _obstacle_cylinder(occ) -> int:
    """Full circle of radius R, centred at (OX, 0, OZ), in X-Z plane (Y=0).

    Built from four 90-degree arcs to allow arbitrary refinement.
    Points: centre, then four cardinal points on the circle.
    """
    pc = occ.addPoint(OX,     0.0, OZ)      # centre
    p0 = occ.addPoint(OX + R, 0.0, OZ)      # (2.75, 0, 0)  — rightmost (+X)
    p1 = occ.addPoint(OX,     0.0, OZ + R)  # (2.5,  0, 0.25) — top (+Z)
    p2 = occ.addPoint(OX - R, 0.0, OZ)      # (2.25, 0, 0)  — leftmost (-X)
    p3 = occ.addPoint(OX,     0.0, OZ - R)  # (2.5,  0, -0.25) — bottom (-Z)

    # Four quarter-circle arcs going counter-clockwise (viewed from +Y):
    # +X → +Z → -X → -Z → +X
    arc0 = occ.addCircleArc(p0, pc, p1)  # right to top
    arc1 = occ.addCircleArc(p1, pc, p2)  # top to left
    arc2 = occ.addCircleArc(p2, pc, p3)  # left to bottom
    arc3 = occ.addCircleArc(p3, pc, p0)  # bottom to right

    cl   = occ.addCurveLoop([arc0, arc1, arc2, arc3])
    surf = occ.addPlaneSurface([cl])
    return surf


def _obstacle_square(occ) -> int:
    """Axis-aligned square, side D, centred at (OX, 0, OZ), in X-Z plane (Y=0)."""
    half = D / 2.0
    p0 = occ.addPoint(OX - half, 0.0, OZ - half)  # SW: (2.25, 0, -0.25)
    p1 = occ.addPoint(OX + half, 0.0, OZ - half)  # SE: (2.75, 0, -0.25)
    p2 = occ.addPoint(OX + half, 0.0, OZ + half)  # NE: (2.75, 0, +0.25)
    p3 = occ.addPoint(OX - half, 0.0, OZ + half)  # NW: (2.25, 0, +0.25)

    l0 = occ.addLine(p0, p1)  # bottom edge (z = -0.25)
    l1 = occ.addLine(p1, p2)  # right edge  (x = +2.75)
    l2 = occ.addLine(p2, p3)  # top edge    (z = +0.25)
    l3 = occ.addLine(p3, p0)  # left edge   (x = +2.25)

    cl   = occ.addCurveLoop([l0, l1, l2, l3])
    surf = occ.addPlaneSurface([cl])
    return surf


def _obstacle_half_cylinder(occ) -> int:
    """D-shape: flat face upstream (x=OX), curved half downstream.

    Flat face at x = OX = 2.5 spanning z in [-R, +R].
    Curved half-circle from (OX, 0, +R) through (OX+R, 0, 0) to (OX, 0, -R).
    """
    pc      = occ.addPoint(OX,     0.0,  0.0)  # arc centre (on flat face)
    p_top   = occ.addPoint(OX,     0.0,  R)    # (2.5, 0, +0.25) — top of flat face
    p_right = occ.addPoint(OX + R, 0.0,  0.0)  # (3.0, 0,  0)    — downstream tip
    p_bot   = occ.addPoint(OX,     0.0, -R)    # (2.5, 0, -0.25) — bottom of flat face

    flat = occ.addLine(p_bot, p_top)            # flat upstream face
    arc1 = occ.addCircleArc(p_top,  pc, p_right)  # top-right quarter arc
    arc2 = occ.addCircleArc(p_right, pc, p_bot)   # right-bottom quarter arc

    cl   = occ.addCurveLoop([flat, arc1, arc2])
    surf = occ.addPlaneSurface([cl])
    return surf


def _obstacle_triangle(occ) -> int:
    """Equilateral triangle: apex upstream (+X direction), base downstream.

    Side = D = 0.5 m. Centroid at (OX, 0, OZ).
    h = D * sqrt(3) / 2.
    Apex at x = OX - 2h/3 (≈ 2.211), z = 0.
    Base vertices at x = OX + h/3 (≈ 2.644), z = +/-D/2 (= +/-0.25).
    """
    h      = D * math.sqrt(3.0) / 2.0   # ≈ 0.4330 m
    x_apex = OX - 2.0 * h / 3.0         # ≈ 2.2113
    x_base = OX + h / 3.0               # ≈ 2.6443

    p_apex  = occ.addPoint(x_apex, 0.0,  0.0)
    p_btop  = occ.addPoint(x_base, 0.0,  D / 2.0)   # (2.644, 0, +0.25)
    p_bbot  = occ.addPoint(x_base, 0.0, -D / 2.0)   # (2.644, 0, -0.25)

    l1 = occ.addLine(p_apex, p_btop)   # leading edge (apex → top)
    l2 = occ.addLine(p_btop, p_bbot)  # base (downstream)
    l3 = occ.addLine(p_bbot, p_apex)  # trailing edge (bottom → apex)

    cl   = occ.addCurveLoop([l1, l2, l3])
    surf = occ.addPlaneSurface([cl])
    return surf


# Map shape name → obstacle surface builder
SHAPE_BUILDERS = {
    "cylinder":      _obstacle_cylinder,
    "square":        _obstacle_square,
    "half_cylinder": _obstacle_half_cylinder,
    "triangle":      _obstacle_triangle,
}


# ---------------------------------------------------------------------------
# Main mesh builder
# ---------------------------------------------------------------------------

def default_out_path(shape: str, raf: float) -> str:
    """Default .msh path beside this script: shape_<name>_raf<n>.msh."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(script_dir, f"shape_{shape}_raf{int(raf)}.msh")


def build_mesh(shape: str, raf: float = 2.0, out_file: str = None) -> None:
    """Generate a 3D hex/prism mesh and write Gmsh v2.2 to out_file.

    Parameters
    ----------
    shape    : obstacle shape — one of 'cylinder', 'square', 'half_cylinder',
               'triangle'
    raf      : refinement multiplier — higher gives more cells (default 2)
    out_file : output path; defaults to shape_<name>_raf<n>.msh beside this script
    """
    if out_file is None:
        out_file = default_out_path(shape, raf)

    print(f"\n{'='*60}")
    print(f"Building mesh: shape={shape}, raf={raf}, out={out_file}")
    print(f"{'='*60}")

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.model.add(f"bluff_{shape}")

        occ = gmsh.model.occ

        # ------------------------------------------------------------------
        # Step 1: Build 2D fluid surface in the X-Z plane at Y=0
        # ------------------------------------------------------------------
        # Domain rectangle via explicit points (all Y=0, coords in X and Z).
        p_dom = [
            occ.addPoint(0.0, 0.0, -LZ / 2.0),  # SW: (0,  0, -2.5)
            occ.addPoint(LX,  0.0, -LZ / 2.0),  # SE: (10, 0, -2.5)
            occ.addPoint(LX,  0.0,  LZ / 2.0),  # NE: (10, 0, +2.5)
            occ.addPoint(0.0, 0.0,  LZ / 2.0),  # NW: (0,  0, +2.5)
        ]
        l_dom = [
            occ.addLine(p_dom[0], p_dom[1]),  # bottom (z = -LZ/2)
            occ.addLine(p_dom[1], p_dom[2]),  # outlet (x = LX)
            occ.addLine(p_dom[2], p_dom[3]),  # top    (z = +LZ/2)
            occ.addLine(p_dom[3], p_dom[0]),  # inlet  (x = 0)
        ]
        cl_dom   = occ.addCurveLoop([l_dom[0], l_dom[1], l_dom[2], l_dom[3]])
        dom_surf = occ.addPlaneSurface([cl_dom])

        # Obstacle surface (all points at Y=0)
        obs_surf = SHAPE_BUILDERS[shape](occ)
        occ.synchronize()

        # Boolean cut: fluid_surface = domain - obstacle
        cut_result, _ = occ.cut(
            [(2, dom_surf)],
            [(2, obs_surf)],
            removeObject=True,
            removeTool=True,
        )
        occ.synchronize()

        if not cut_result:
            raise RuntimeError(
                f"Boolean cut produced no output for shape={shape!r}. "
                "Ensure obstacle lies strictly inside the domain."
            )
        fluid_2d_tag = cut_result[0][1]

        # ------------------------------------------------------------------
        # Step 2: Classify 2D boundary curves for later mesh-field setup
        # ------------------------------------------------------------------
        # Query the boundary of the (cut) fluid surface; classify each curve
        # by its bounding box position relative to the domain boundary.
        fluid_bnd = gmsh.model.getBoundary(
            [(2, fluid_2d_tag)], oriented=False, recursive=False
        )
        bnd_curve_tags = [abs(t) for _, t in fluid_bnd]

        TOL = 1e-3
        obstacle_curves_2d: List[int] = []

        for ct in bnd_curve_tags:
            bb = gmsh.model.getBoundingBox(1, ct)
            xmin, ymin, zmin, xmax, ymax, zmax = bb
            on_inlet   = abs(xmin) < TOL and abs(xmax) < TOL
            on_outlet  = abs(xmin - LX) < TOL and abs(xmax - LX) < TOL
            on_zbottom = abs(zmin + LZ / 2.0) < TOL and abs(zmax + LZ / 2.0) < TOL
            on_ztop    = abs(zmin - LZ / 2.0) < TOL and abs(zmax - LZ / 2.0) < TOL
            if not (on_inlet or on_outlet or on_zbottom or on_ztop):
                obstacle_curves_2d.append(ct)

        print(f"  Obstacle boundary curves (2D): {obstacle_curves_2d}")
        if not obstacle_curves_2d:
            # Debug: print all bounding boxes
            print("  All 2D boundary curves and bounding boxes:")
            for ct in bnd_curve_tags:
                bb = gmsh.model.getBoundingBox(1, ct)
                print(f"    curve {ct}: {[round(v, 4) for v in bb]}")
            raise RuntimeError(
                f"Could not identify obstacle boundary curves for shape={shape!r}."
            )

        # ------------------------------------------------------------------
        # Step 3: Extrude the 2D fluid surface in +Y to produce the 3D mesh
        # ------------------------------------------------------------------
        ext = occ.extrude(
            [(2, fluid_2d_tag)],
            0.0, LY, 0.0,    # translate in +Y
            numElements=[1],
            recombine=True,
        )
        occ.synchronize()
        # ext structure: per input surface → [top_surf, volume, side_surf0, ...]
        # ext[0] = (2, top_surf_tag)  — the y=LY face
        # ext[1] = (3, vol_tag)       — the volume
        # ext[2..] = (2, side_surf_tags) — extruded sides in curve-loop order

        # ------------------------------------------------------------------
        # Step 4: Mesh size fields (Distance + Threshold from obstacle wall)
        # ------------------------------------------------------------------
        # After extrusion, the obstacle 2D curves became 3D surfaces.
        # We query the obstacle wall surfaces by their bounding box.
        # But it's easier to use the 2D obstacle curves as distance sources —
        # gmsh fields operate on curves that exist in 3D context.
        #
        # The 2D curves at Y=0 are still present after extrusion and are the
        # bottom edges of the obstacle wall surfaces. Use them as distance source.

        base_near = 0.05    # element size near obstacle at raf=1
        base_far  = 0.25    # element size far from obstacle at raf=1
        near_size = base_near / raf
        far_size  = base_far  / raf

        f_dist = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(f_dist, "CurvesList", obstacle_curves_2d)
        gmsh.model.mesh.field.setNumber(f_dist,  "Sampling",   500)

        f_thresh = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(f_thresh, "InField",  f_dist)
        gmsh.model.mesh.field.setNumber(f_thresh, "SizeMin",  near_size)
        gmsh.model.mesh.field.setNumber(f_thresh, "SizeMax",  far_size)
        gmsh.model.mesh.field.setNumber(f_thresh, "DistMin",  near_size * 0.5)
        gmsh.model.mesh.field.setNumber(f_thresh, "DistMax",  D * 5.0)
        gmsh.model.mesh.field.setAsBackgroundMesh(f_thresh)

        # ------------------------------------------------------------------
        # Step 5: Mesh options — quad-dominant with Blossom recombination
        # ------------------------------------------------------------------
        gmsh.option.setNumber("Mesh.RecombineAll",           1)
        gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 1)  # Blossom
        gmsh.option.setNumber("Mesh.Algorithm",              8)  # Frontal-Delaunay quads
        gmsh.option.setNumber("Mesh.SubdivisionAlgorithm",   1)  # all-quads subdivision

        # ------------------------------------------------------------------
        # Step 6: Generate 3D mesh
        # ------------------------------------------------------------------
        gmsh.model.mesh.generate(3)

        # ------------------------------------------------------------------
        # Step 7: Identify and assign Physical Groups by bounding box
        # ------------------------------------------------------------------
        all_surf_tags = [t for _, t in gmsh.model.getEntities(2)]
        all_vol_tags  = [t for _, t in gmsh.model.getEntities(3)]

        inlet_surfs  = []
        outlet_surfs = []
        sym_surfs    = []
        updown_surfs = []
        cyl_surfs    = []

        for t in all_surf_tags:
            bb = gmsh.model.getBoundingBox(2, t)
            xmin, ymin, zmin, xmax, ymax, zmax = bb

            if abs(xmin) < TOL and abs(xmax) < TOL:
                inlet_surfs.append(t)
            elif abs(xmin - LX) < TOL and abs(xmax - LX) < TOL:
                outlet_surfs.append(t)
            elif (abs(ymin) < TOL and abs(ymax) < TOL) or \
                 (abs(ymin - LY) < TOL and abs(ymax - LY) < TOL):
                sym_surfs.append(t)
            elif (abs(zmin + LZ / 2.0) < TOL and abs(zmax + LZ / 2.0) < TOL) or \
                 (abs(zmin - LZ / 2.0) < TOL and abs(zmax - LZ / 2.0) < TOL):
                updown_surfs.append(t)
            else:
                cyl_surfs.append(t)

        # Sanity checks — fail loudly rather than producing a silently broken mesh
        for name, lst in [
            ("inlet",    inlet_surfs),
            ("outlet",   outlet_surfs),
            ("symmetry", sym_surfs),
            ("updown",   updown_surfs),
            ("cylindre", cyl_surfs),
        ]:
            if not lst:
                print(f"\n  DEBUG: All surface bounding boxes:")
                for t in all_surf_tags:
                    print(f"    surf {t}: {[round(v, 4) for v in gmsh.model.getBoundingBox(2, t)]}")
                raise RuntimeError(
                    f"Physical group '{name}' found no surfaces "
                    f"(shape={shape!r}). Check bounding-box logic."
                )

        gmsh.model.addPhysicalGroup(2, inlet_surfs,  tag=1,  name="inlet")
        gmsh.model.addPhysicalGroup(2, outlet_surfs, tag=2,  name="outlet")
        gmsh.model.addPhysicalGroup(2, cyl_surfs,    tag=3,  name="cylindre")
        gmsh.model.addPhysicalGroup(2, sym_surfs,    tag=4,  name="symmetry")
        gmsh.model.addPhysicalGroup(2, updown_surfs, tag=5,  name="updown")
        gmsh.model.addPhysicalGroup(3, all_vol_tags, tag=10, name="fluid")

        # ------------------------------------------------------------------
        # Step 8: Summary
        # ------------------------------------------------------------------
        elem_types, elem_tags, _ = gmsh.model.mesh.getElements(3)
        total_3d    = sum(len(et) for et in elem_tags)
        hex_count   = sum(len(et) for etype, et in zip(elem_types, elem_tags) if etype == 5)
        prism_count = sum(len(et) for etype, et in zip(elem_types, elem_tags) if etype == 6)
        node_count  = len(gmsh.model.mesh.getNodes()[0])

        print(f"\n  --- Mesh summary ---")
        print(f"  Shape    : {shape}")
        print(f"  raf      : {raf}")
        print(f"  Nodes    : {node_count}")
        print(f"  3D cells : {total_3d}  (hex={hex_count}, prism={prism_count})")
        print(f"  Physical groups:")
        for dim, tag in sorted(gmsh.model.getPhysicalGroups()):
            name_g   = gmsh.model.getPhysicalName(dim, tag)
            n_ents   = len(gmsh.model.getEntitiesForPhysicalGroup(dim, tag))
            print(f"    dim={dim} tag={tag:2d} name={name_g!r:12s} n_entities={n_ents}")

        # ------------------------------------------------------------------
        # Step 9: Write mesh
        # ------------------------------------------------------------------
        gmsh.write(out_file)
        fsize_kb = os.path.getsize(out_file) // 1024
        print(f"  Written  : {out_file}  ({fsize_kb} kB)")

    finally:
        gmsh.finalize()


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_mesh(path: str) -> bool:
    """Re-open a written .msh in a fresh gmsh session and verify correctness.

    Checks:
    - All 6 required physical groups present with correct names and tags.
    - Global bounding box matches the domain.
    - At least some 3D elements exist.

    Returns True on success.
    """
    print(f"\n  Verifying: {path}")
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.open(path)

        expected = {
            (2, 1, "inlet"),
            (2, 2, "outlet"),
            (2, 3, "cylindre"),
            (2, 4, "symmetry"),
            (2, 5, "updown"),
            (3, 10, "fluid"),
        }
        found = set()
        for dim, tag in gmsh.model.getPhysicalGroups():
            name = gmsh.model.getPhysicalName(dim, tag)
            found.add((dim, tag, name))

        missing = expected - found
        if missing:
            print(f"  VERIFY FAIL: missing groups: {missing}")
            return False

        bb = gmsh.model.getBoundingBox(-1, -1)
        xmin, ymin, zmin, xmax, ymax, zmax = bb
        tol = 0.05
        bb_ok = (
            abs(xmin) < tol       and abs(xmax - LX) < tol and
            abs(ymin) < tol       and abs(ymax - LY) < tol and
            abs(zmin + LZ / 2.0) < tol and abs(zmax - LZ / 2.0) < tol
        )
        if not bb_ok:
            print(f"  VERIFY FAIL: bounding box {list(bb)} does not match "
                  f"expected [0,{LX}] x [0,{LY}] x [{-LZ/2},{LZ/2}]")
            return False

        etypes, etags, _ = gmsh.model.mesh.getElements(3)
        n3d   = sum(len(et) for et in etags)
        hex_n = sum(len(et) for et, etype in zip(etags, etypes) if etype == 5)
        prism_n = sum(len(et) for et, etype in zip(etags, etypes) if etype == 6)
        if n3d == 0:
            print(f"  VERIFY FAIL: no 3D elements")
            return False

        print(f"  VERIFY OK : {os.path.basename(path)}  "
              f"n3d={n3d} (hex={hex_n}, prism={prism_n})")
        return True

    finally:
        gmsh.finalize()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Generate 2D bluff-body mesh for Code_Saturne shape-comparison study. "
            "Produces a Gmsh v2.2 .msh with hex/prism elements and physical "
            "surface/volume groups that match setup.xml selectors."
        )
    )
    parser.add_argument(
        "--shape",
        choices=list(SHAPE_BUILDERS.keys()),
        required=True,
        help="Obstacle shape.",
    )
    parser.add_argument(
        "--raf",
        type=float,
        default=2.0,
        help="Refinement multiplier (default 2; higher = finer mesh).",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Output .msh filename. Relative paths are resolved from the "
             "script directory. Default: shape_<name>_raf<n>.msh.",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        default=False,
        help="Skip post-write mesh verification.",
    )
    args = parser.parse_args()

    # Resolve output path
    if args.out is not None and not os.path.isabs(args.out):
        args.out = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), args.out
        )

    build_mesh(shape=args.shape, raf=args.raf, out_file=args.out)

    # Determine actual output path for verification
    actual_out = args.out if args.out is not None else default_out_path(args.shape, args.raf)

    if not args.no_verify and os.path.exists(actual_out):
        ok = verify_mesh(actual_out)
        sys.exit(0 if ok else 1)
