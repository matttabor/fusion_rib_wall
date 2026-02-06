# geometry.py
#
# OrganicFlowRibs (Legacy-Stable + Explicit Orientation)
# -----------------------------------------------------
# This file is a merge-safe, single-source-of-truth geometry module based on the
# original working single-file generator (wavy.py), ported into the split project.
#
# Goal: preserve the legacy output you approved (waves/feel/tabs/spacing) while
# making the final orientation deterministic (no more "Fusion did something weird").
#
# IMPORTANT: We intentionally preserve the legacy coordinate quirk that produces
# the desired look:
#   - Sketch is created on the XZ construction plane
#   - But spline points are emitted as (x, z, 0)
# Fusion tolerates this and it matches the legacy result.
#
# If/when we do "Stage 2 normalization", we can remove that quirk safely.

import adsk.core
import adsk.fusion
import math
import random

from util import cm

# Keep this TRUE to match the legacy look.
LEGACY_POINT_QUIRK = True

# Explicit orientation control (you found flipping to -1 was the key).
# If you ever need to flip the final orientation, change this to +1.
ORIENT_SIGN = -1 
ORIENT_AXIS = 'Y'   # 'X', 'Y', or 'Z'
ORIENT_DEG  = -90   # degrees

ORIENT2_AXIS = 'Z'  # optional
ORIENT2_DEG  = 0    # set to 180 to flip, etc


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
    ui = adsk.core.Application.get().userInterface

    # Defensive clamps (match legacy feel)
    rib_count = max(1, int(rib_count))
    samples = max(40, int(samples))
    rib_length_in = max(0.01, float(rib_length_in))
    rib_height_in = max(0.01, float(rib_height_in))
    rib_thickness_in = max(0.01, float(rib_thickness_in))
    gap_between_ribs_in = max(0.0, float(gap_between_ribs_in))

    randomness = max(0.0, min(1.0, float(randomness)))
    wildness = max(0.0, min(1.0, float(wildness)))
    smoothness = max(0.0, min(1.0, float(smoothness)))

    base_amp_in = min(float(base_amplitude_in), rib_height_in)
    base_period_in = max(0.01, float(bend_scale_in))  # legacy "wavePeriod" equivalent
    pitch_in = rib_thickness_in + gap_between_ribs_in

    # Container component
    container_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    container_comp = container_occ.component
    container_comp.name = f"{name_prefix}{rib_count}x_seed{seed}"
    occs = container_comp.occurrences
    rib_occs = []  # track rib occurrences so we can apply final orientation per-rib

    # Precompute tab spans along rib length
    tab_spans = []
    if add_tabs:
        centers = tab_centers_in or []
        for c in centers:
            x0 = max(0.0, float(c) - tab_width_in / 2.0)
            x1 = min(rib_length_in, float(c) + tab_width_in / 2.0)
            if x1 > x0:
                tab_spans.append((x0, x1))
        tab_spans.sort(key=lambda t: t[0], reverse=True)

    # Master RNG (repeatability)
    master = random.Random(int(seed))

    # Bulge profile across ribs (legacy topography feel)
    if rib_count > 1:
        center = (rib_count - 1) * (0.35 + 0.30 * master.random())
    else:
        center = 0.0
    sigma = max(1.0, rib_count * (0.14 + 0.10 * master.random()))

    # Coupling term that can sweep diagonally across ribs
    diag_strength = (2.0 * math.pi) * (0.5 + 4.0 * wildness) * (0.25 + 0.75 * randomness)

    # End fade envelope (keep edges clean)
    fade_power = 1.8 + 1.4 * smoothness

    def envelope(x_in: float, rib_rng: random.Random) -> float:
        shift = (rib_rng.uniform(-0.08, 0.08)) * (wildness * 0.7 + randomness * 0.3)
        t = (x_in / rib_length_in) + shift
        t = max(0.0, min(1.0, t))
        return math.pow(math.sin(math.pi * t), fade_power)

    # Build per-rib params (amp drift + bulge)
    rib_params = []
    for i in range(rib_count):
        rib_rng = random.Random(int(seed) + i * 10007)

        amp_var = 0.25
        per_var = 0.30
        phase_jitter = 0.25

        Ai = base_amp_in * (1.0 + (amp_var * randomness) * rib_rng.uniform(-1.0, 1.0))
        Pi = base_period_in * (1.0 + (per_var * randomness) * rib_rng.uniform(-1.0, 1.0))
        Pi = max(3.0, Pi)

        phi0 = rib_rng.uniform(0.0, 2.0 * math.pi) * (phase_jitter * randomness)

        bulge = 1.0
        bulge_strength = 0.35
        if rib_count > 1:
            d = (i - center) / sigma
            bulge = 1.0 + bulge_strength * randomness * math.exp(-(d * d))

        rib_params.append((Ai, Pi, phi0, bulge))

    # Progress dialog
    prog = ui.createProgressDialog()
    prog.isBackgroundTranslucent = False
    prog.show("OrganicFlowRibs", "Generating rib %v of %m", 0, max(1, rib_count), 0)

    try:
        for i in range(rib_count):
            prog.progressValue = i + 1
            adsk.doEvents()

            rib_occ = occs.addNewComponent(adsk.core.Matrix3D.create())
            rib_occs.append(rib_occ)
            rib_comp = rib_occ.component
            rib_comp.name = f"Rib_{i+1:02d}"

            # Sketch (legacy: XZ plane, points emitted as (x, z, 0))
            sk = rib_comp.sketches.add(rib_comp.xZConstructionPlane)
            curves = sk.sketchCurves
            lines = curves.sketchLines
            splines = curves.sketchFittedSplines

            rib_rng = random.Random(int(seed) + i * 10007)
            Ai, Pi, phi0, bulge = rib_params[i]

            rib_t = 0.0 if rib_count == 1 else (i / (rib_count - 1))

            fitPts = adsk.core.ObjectCollection.create()
            for s in range(samples + 1):
                x_in = rib_length_in * s / samples

                env = envelope(x_in, rib_rng)
                diag = diag_strength * (rib_t - 0.5) * (x_in / rib_length_in)

                z_in = rib_height_in - (env * (Ai * bulge)) * math.sin((2.0 * math.pi * x_in / Pi) + phi0 + diag)
                z_in = max(0.0, min(rib_height_in, z_in))

                # Legacy coordinate quirk:
                fitPts.add(adsk.core.Point3D.create(cm(x_in), cm(z_in), 0))

            splines.add(fitPts)

            # Close profile down to baseline (with optional tabs to negative z)
            x_right = rib_length_in
            z_right_in = fitPts.item(fitPts.count - 1).y / 2.54  # y holds "z" in legacy quirk

            lines.addByTwoPoints(
                adsk.core.Point3D.create(cm(x_right), cm(z_right_in), 0),
                adsk.core.Point3D.create(cm(x_right), cm(0.0), 0)
            )

            cur_x = rib_length_in
            baseline_z = 0.0
            tab_bottom_z = -tab_height_in

            def P(xi, zi):
                return adsk.core.Point3D.create(cm(xi), cm(zi), 0)

            p = P(cur_x, baseline_z)

            if add_tabs and len(tab_spans) > 0:
                for (t0, t1) in tab_spans:
                    if cur_x > t1:
                        p2 = P(t1, baseline_z)
                        lines.addByTwoPoints(p, p2)
                        p = p2
                        cur_x = t1

                    # Down
                    p2 = P(cur_x, tab_bottom_z)
                    lines.addByTwoPoints(p, p2)
                    p = p2

                    # Left
                    p2 = P(t0, tab_bottom_z)
                    lines.addByTwoPoints(p, p2)
                    p = p2
                    cur_x = t0

                    # Up
                    p2 = P(cur_x, baseline_z)
                    lines.addByTwoPoints(p, p2)
                    p = p2

                if cur_x > 0.0:
                    p2 = P(0.0, baseline_z)
                    lines.addByTwoPoints(p, p2)
                    p = p2
                    cur_x = 0.0
            else:
                p2 = P(0.0, baseline_z)
                lines.addByTwoPoints(p, p2)
                p = p2
                cur_x = 0.0

            # Close back up to curve start
            z_left_in = fitPts.item(0).y / 2.54
            lines.addByTwoPoints(P(0.0, baseline_z), P(0.0, z_left_in))

            if sk.profiles.count == 0:
                ui.messageBox(f"Profile failed on rib {i+1}. Try lowering amplitude or tab height.")
                return

            prof = sk.profiles.item(0)

            # Extrude thickness along +Y (legacy behavior)
            ext = rib_comp.features.extrudeFeatures
            ei = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            ei.setDistanceExtent(False, adsk.core.ValueInput.createByString(f"{rib_thickness_in} in"))
            ext.add(ei)
    
            # Place rib occurrences (legacy behavior)
            m = adsk.core.Matrix3D.create()
            if layout_along_y:
                m.translation = adsk.core.Vector3D.create(0, cm(i * pitch_in), 0)
            else:
                m.translation = adsk.core.Vector3D.create(cm(i * pitch_in), 0, 0)
            rib_occ.transform = m

        # Final orientation: rotate EACH rib occurrence in-place (about its own pivot).
        # This avoids edge cases where the container transform doesn't affect the first rib.
        axis = adsk.core.Vector3D.create(0, 1, 0)
        for ro in rib_occs:
           
            t = ro.transform.translation
            pivot = adsk.core.Point3D.create(t.x, t.y, t.z)
            rot = adsk.core.Matrix3D.create()
            rot.setToRotation(
                ORIENT_SIGN * (math.pi / 2),
                axis,
                pivot
            )
            cur = ro.transform.copy()
            cur.transformBy(rot)
            ro.transform = cur

    finally:
        prog.hide()
