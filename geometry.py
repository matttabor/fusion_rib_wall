# geometry.py
#
# OrganicFlowRibs (Axis-Fix: X=thickness/stack, Y=height (48"), Z=wave)
# --------------------------------------------------------------------
# Based on your latest "orientation is wrong", this version uses the most
# common Fusion interpretation for your screenshots:
#
#   - X : rib THICKNESS direction AND stack direction (thickness + gap)
#   - Y : rib HEIGHT (vertical), default 48"
#   - Z : RELIEF / wave depth (varies), back plane at Z=0
#
# Side section view (looking along +X or -X):
#   - Back of rib is a straight line at Z=0
#   - Only the FRONT varies: Z = f(ribIndex, Y) and is clamped >= 0
#   - Ends are flat at Y=0 and Y=rib_length_in
#
# Construction:
#   1) Build CLOSED profile in the YZ plane:
#        - back edge: Z=0 from Y=0..rib_length_in
#        - front edge: fitted spline through (Y, Z(Y))
#        - close with flat top/bottom edges
#   2) Extrude along +X by rib_thickness_in (0.75")
#   3) Stack along +X by pitch = rib_thickness_in + gap_between_ribs_in
#
# Tabs/notches: intentionally disabled until the core orientation is locked.

import adsk.core
import adsk.fusion
import math
import random

from util import cm, smooth_series


def generate_flow_ribs(
    root,
    name_prefix: str,

    seed: int,

    rib_count: int,
    rib_length_in: float,      # HEIGHT along Y (48")
    rib_height_in: float,      # MAX RELIEF depth along Z
    rib_thickness_in: float,   # thickness/stack along X (0.75")
    gap_between_ribs_in: float,
    layout_along_y: bool,      # ignored in this mode

    randomness: float,
    wildness: float,
    smoothness: float,

    base_amplitude_in: float,  # relief amplitude driver (Z)
    bend_scale_in: float,
    flow_angle_rad: float,
    flow_strength: float,
    detail: float,

    use_mass: bool,
    mass_strength: float,

    samples: int,
    smooth_passes: int,

    add_tabs: bool,
    tab_width_in: float,
    tab_height_in: float,
    tab_centers_in
):
    app = adsk.core.Application.get()
    ui = app.userInterface

    progress = ui.createProgressDialog()
    progress.isBackgroundTranslucent = False
    progress.show("OrganicFlowRibs", "Generating rib %v of %m", 0, max(1, rib_count), 0)

    container_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    container_comp = container_occ.component
    container_comp.name = f"{name_prefix}{rib_count}x_seed{seed}"
    rib_occs = container_comp.occurrences

    pitch_in = rib_thickness_in + gap_between_ribs_in
    total_span_in = (rib_count - 1) * pitch_in if rib_count > 1 else 0.0

    rng = random.Random(seed)
    TAU = 2.0 * math.pi

    # Flow-space rotation in (X,Y) domain: coherence across ribs (X) and along height (Y)
    ca = math.cos(flow_angle_rad)
    sa = math.sin(flow_angle_rad)

    def rot_u(x, y):
        return x * ca + y * sa

    def rot_v(x, y):
        return -x * sa + y * ca

    def end_env(y_in: float) -> float:
        # Calm near ends (top/bottom)
        if rib_length_in <= 0.0:
            return 1.0
        t = max(0.0, min(1.0, y_in / rib_length_in))
        p = 1.6 + 0.9 * smoothness
        return math.pow(math.sin(math.pi * t), p)

    scale_u = max(total_span_in + pitch_in, 0.001)
    scale_v = max(rib_length_in, 0.001)

    base_period_u = max(bend_scale_in, scale_u * 0.6)
    base_period_v = max(bend_scale_in, scale_v * 0.55)

    amp = max(0.0, base_amplitude_in) * (0.55 + 0.75 * randomness) * max(0.0, min(1.0, flow_strength))
    amp = min(amp, max(0.001, rib_height_in))

    detail_mix = max(0.0, min(1.0, detail)) * (0.35 + 0.65 * wildness)

    ph1 = rng.uniform(0.0, TAU)
    ph2 = rng.uniform(0.0, TAU)
    ph3 = rng.uniform(0.0, TAU)

    def relief_z(x_pos_in: float, y_in: float) -> float:
        u = rot_u(x_pos_in, y_in)
        v = rot_v(x_pos_in, y_in)

        s = 0.0
        s += 0.90 * math.sin(TAU * (u / max(0.001, base_period_u)) + ph1)
        s += 0.55 * math.sin(TAU * (v / max(0.001, base_period_v)) + ph2)

        if detail_mix > 1e-6:
            s += detail_mix * 0.45 * math.sin(TAU * (u / max(0.001, base_period_u * 0.45)) + ph3)

        s *= 0.55
        s *= end_env(y_in)
        return amp * s

    try:
        for i in range(rib_count):
            progress.progressValue = i + 1
            adsk.doEvents()

            rib_occ = rib_occs.addNewComponent(adsk.core.Matrix3D.create())
            rib_comp = rib_occ.component
            rib_comp.name = f"Rib_{i+1:02d}"

            x_pos_in = i * pitch_in

            # Profile in YZ plane (Y=height, Z=relief)
            sketch = rib_comp.sketches.add(rib_comp.yZConstructionPlane)
            curves = sketch.sketchCurves
            lines = curves.sketchLines
            splines = curves.sketchFittedSplines

            y_vals = []
            z_vals = []
            for s in range(samples + 1):
                y_in = rib_length_in * (s / max(1, samples))
                y_vals.append(y_in)
                z_vals.append(relief_z(x_pos_in, y_in))

            z_vals = smooth_series(z_vals, passes=smooth_passes)

            # Shift so min touches back plane Z=0
            z_min = min(z_vals) if z_vals else 0.0
            z_shifted = [(z - z_min) for z in z_vals]
            z_final = [max(0.0, min(rib_height_in, z)) for z in z_shifted]

            # Front spline: (Y, Z)
            front_pts = adsk.core.ObjectCollection.create()
            for y_in, z_in in zip(y_vals, z_final):
                front_pts.add(adsk.core.Point3D.create(0, cm(y_in), cm(z_in)))
            splines.add(front_pts)

            # Close with flat top/bottom and flat back at Z=0
            top_front = adsk.core.Point3D.create(0, cm(rib_length_in), cm(z_final[-1] if z_final else 0.0))
            top_back  = adsk.core.Point3D.create(0, cm(rib_length_in), cm(0.0))
            lines.addByTwoPoints(top_front, top_back)

            bot_back  = adsk.core.Point3D.create(0, cm(0.0), cm(0.0))
            lines.addByTwoPoints(top_back, bot_back)

            bot_front = adsk.core.Point3D.create(0, cm(0.0), cm(z_final[0] if z_final else 0.0))
            lines.addByTwoPoints(bot_back, bot_front)

            if sketch.profiles.count == 0:
                ui.messageBox(
                    f"Profile failed on rib {i+1}.\n\n"
                    "Try:\n"
                    "- Increase samples (200–400)\n"
                    "- Increase smooth_passes (2–4)\n"
                    "- Reduce detail/wildness/randomness"
                )
                return

            prof = sketch.profiles.item(0)

            # Extrude along +X by thickness
            extrudes = rib_comp.features.extrudeFeatures
            ext_in = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByString(f"{rib_thickness_in} in"))
            extrudes.add(ext_in)

            # Stack along +X (thickness + gap)
            m = adsk.core.Matrix3D.create()
            m.translation = adsk.core.Vector3D.create(cm(x_pos_in), 0, 0)
            rib_occ.transform = m

    finally:
        progress.hide()

    ui.messageBox(
        "Generated ribs with axis fix.\n\n"
        f"Ribs: {rib_count}\n"
        f"Height (Y): {rib_length_in} in\n"
        f"Thickness (X extrude): {rib_thickness_in} in\n"
        f"Gap between ribs: {gap_between_ribs_in} in\n"
        f"Max relief depth (Z): {rib_height_in} in\n"
        "Back plane: Z=0 (flat). Only front face varies."
    )
