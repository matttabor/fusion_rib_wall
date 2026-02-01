# geometry.py
#
# OrganicFlowRibs (Flowy Footprint Rewrite)
# ----------------------------------------
# This version builds each rib as a curvy “ribbon” footprint in the XY plane
# (so the sides are not straight), then extrudes in +Z for height.
#
# Constraints targeted:
# - No straight lines except:
#   * top and bottom edges (they’re splines but generally “clean”)
#   * back edge (mostly straight, with optional tab notch geometry)
# - Optional tab NOTCH cut into the back edge of each rib (for a back panel to slot into)
# - After generation: rotate the entire container -90° about X so ribs are oriented for real-life “standing” layout.
#
# Notes:
# - We keep your signature and many parameters.
# - `tab_centers_in` is kept for compatibility but this rewrite uses per-rib notch placement
#   (centered on the rib’s local Y = 0). If you later want “multiple notches per rib”
#   or “notches aligned to global backboard features,” we can extend it.

import adsk.core
import adsk.fusion
import math
import random

from util import cm, smooth_series, build_tab_spans


def generate_flow_ribs(
    root,
    name_prefix: str,

    seed: int,

    rib_count: int,
    rib_length_in: float,
    rib_height_in: float,
    rib_thickness_in: float,
    gap_between_ribs_in: float,
    layout_along_y: bool,

    randomness: float,
    wildness: float,
    smoothness: float,

    base_amplitude_in: float,
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
    progress = ui.createProgressDialog()
    progress.isBackgroundTranslucent = False
    progress.show("OrganicFlowRibs", "Generating rib %v of %m", 0, max(1, rib_count), 0)

    # ----------------------------
    # Container component
    # ----------------------------
    container_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    container_comp = container_occ.component
    container_comp.name = f"{name_prefix}{rib_count}x_seed{seed}"
    rib_occs = container_comp.occurrences

    # Pitch: thickness + gap (spacing between rib centers)
    pitch_in = rib_thickness_in + gap_between_ribs_in
    total_span_in = (rib_count - 1) * pitch_in if rib_count > 1 else 0.0

    # ----------------------------
    # Flow-space rotation (u,v)
    # ----------------------------
    master = random.Random(seed)

    ca = math.cos(flow_angle_rad)
    sa = math.sin(flow_angle_rad)

    def rot_u(x, y):
        # Along flow direction
        return x * ca + y * sa

    def rot_v(x, y):
        # Perpendicular to flow direction
        return -x * sa + y * ca

    TAU = 2.0 * math.pi

    # Reference-ish period to keep a faint “directional” component
    primary_period = max(bend_scale_in, rib_length_in * 1.25)

    # Coherent drift across ribs (subtle, but helps avoid “stamping”)
    y_phase_strength = (2.0 * math.pi) * (0.06 + 0.90 * wildness) * flow_strength * (0.25 + 0.75 * randomness)
    phase2 = ((seed % 100000) / 100000.0) * (2.0 * math.pi)

    # Sculpture scale used to pick reasonable wavelengths
    panel_scale = max(rib_length_in, (total_span_in + pitch_in), 0.001)

    def end_envelope(x_in: float) -> float:
        """
        Fade motion at the ends of the rib length, so ends are calmer/cleaner.
        """
        if rib_length_in <= 0.0:
            return 1.0
        t = max(0.0, min(1.0, x_in / rib_length_in))
        p = 1.4 + 0.8 * smoothness
        return math.pow(math.sin(math.pi * t), p)

    # ----------------------------
    # Multi-angle wave fields + domain warping (pure math)
    # ----------------------------
    def _wave_component(rng: random.Random, scale_in: float):
        theta = rng.uniform(-math.pi, math.pi)
        ux = math.cos(theta)
        uy = math.sin(theta)
        lam = rng.uniform(0.35, 1.25) * max(0.001, scale_in)
        amp = rng.uniform(0.35, 1.0)
        ph = rng.uniform(0.0, TAU)
        return (amp, lam, ux, uy, ph)

    def _make_wave_field(seed_base: int, components: int, out_amp: float, scale_in: float):
        rng = random.Random(seed_base)
        waves = [_wave_component(rng, scale_in) for _ in range(max(1, components))]
        amp_sum = sum(w[0] for w in waves) or 1.0

        def field(u: float, v: float) -> float:
            s = 0.0
            for (a, lam, ux, uy, ph) in waves:
                t = (u * ux + v * uy) / max(0.001, lam)
                s += a * math.sin(TAU * t + ph)
            return out_amp * (s / amp_sum)

        return field

    def _make_warped_field(seed_base: int,
                           out_amp: float,
                           base_scale_in: float,
                           base_components: int,
                           warp_components: int,
                           warp_strength: float,
                           warp_scale: float):
        base = _make_wave_field(seed_base, base_components, 1.0, base_scale_in)
        warp_scale_in = max(0.001, base_scale_in * warp_scale)
        wx = _make_wave_field(seed_base + 101, warp_components, 1.0, warp_scale_in)
        wy = _make_wave_field(seed_base + 202, warp_components, 1.0, warp_scale_in)

        def field(u: float, v: float) -> float:
            du = wx(u, v) * (warp_strength * base_scale_in)
            dv = wy(u, v) * (warp_strength * base_scale_in)
            return out_amp * base(u + du, v + dv)

        return field

    big_field = _make_warped_field(
        seed_base=seed,
        out_amp=1.0,
        base_scale_in=panel_scale,
        base_components=3,
        warp_components=2,
        warp_strength=(0.06 + 0.18 * wildness) * (0.35 + 0.65 * randomness),
        warp_scale=1.8
    )

    small_field = _make_warped_field(
        seed_base=seed + 999,
        out_amp=1.0,
        base_scale_in=panel_scale * 0.55,
        base_components=4,
        warp_components=2,
        warp_strength=(0.04 + 0.10 * wildness) * (0.35 + 0.65 * randomness),
        warp_scale=2.2
    )

    # Optional broad “mass” bulge in (u,v)
    if use_mass and rib_count > 1 and mass_strength > 0.0:
        u_extent = rot_u(rib_length_in, total_span_in if total_span_in > 0 else pitch_in)
        v_extent = rot_v(rib_length_in, total_span_in if total_span_in > 0 else pitch_in)

        u0 = (0.10 + 0.80 * master.random()) * u_extent
        v0 = (0.15 + 0.70 * master.random()) * v_extent

        mass_u_sigma = max(rib_length_in * 0.35, bend_scale_in * 0.25, 0.001)
        mass_v_sigma = max((total_span_in + pitch_in) * 0.35, rib_length_in * 0.25, 0.001)

        # Mass amplitude in “field units”; later multiplied by a lateral amplitude
        mass_amp = (0.35 + 0.65 * mass_strength) * (0.25 + 0.75 * randomness)
    else:
        u0 = v0 = mass_u_sigma = mass_v_sigma = mass_amp = 0.0

    # ----------------------------
    # Lateral (in-plane) flow offset
    # ----------------------------
    # We re-use base_amplitude_in as the “energy” knob, but scale it down and clamp
    # so ribs don’t overlap too aggressively by default.
    #
    # If you want *more* spaghetti, raise flow_strength/detail or increase base_amplitude_in.
    base_lateral_amp_in = max(0.0, base_amplitude_in) * (0.35 + 0.85 * flow_strength) * (0.25 + 0.75 * randomness)

    # Keep lateral motion reasonable vs spacing
    # 1.05 factor gives a noticeable 
    max_lateral = max(0.0, 1.05 * pitch_in)
    lateral_amp_in = min(base_lateral_amp_in, max_lateral)

    def lateral_offset_in(x_in: float, y_global_in: float) -> float:
        """
        Returns a lateral Y offset in inches for the rib centerline at position x.
        y_global_in is the rib's global index position along the array spacing (in inches).
        """
        u = rot_u(x_in, y_global_in)
        v = rot_v(x_in, y_global_in)

        env = end_envelope(x_in)

        yt = 0.0 if total_span_in <= 0 else (y_global_in / total_span_in)
        yphase = y_phase_strength * (yt - 0.5)

        s_big = big_field(u, v)
        s_small = small_field(u, v)

        small_mix = (0.12 + 0.40 * detail) * (0.25 + 0.75 * (1.0 - smoothness))
        small_mix = max(0.0, min(0.80, small_mix))
        big_mix = 1.0 - 0.55 * small_mix

        s = (big_mix * s_big) + (small_mix * s_small)

        # tiny coherent directional component
        s += 0.10 * (0.25 + 0.75 * randomness) * math.sin((u / max(0.001, primary_period)) * TAU + 0.35 * yphase + phase2)

        # optional mass bulge adds bias (still lateral)
        if use_mass and mass_amp != 0.0:
            du = (u - u0) / max(0.001, mass_u_sigma)
            dv = (v - v0) / max(0.001, mass_v_sigma)
            s += mass_amp * math.exp(-(du * du + dv * dv))

        # envelope keeps ends calmer
        return env * lateral_amp_in * s

    # ----------------------------
    # Back-edge tab notch parameters (per rib)
    # ----------------------------
    # Tab notch is a “U” cut into the back edge at x=rib_length:
    # - width is along Y
    # - depth is along X (how far forward the notch cuts)
    #
    # We clamp width to fit within the rib thickness.
    notch_width_in = min(max(0.0, tab_width_in), max(0.0, rib_thickness_in * 0.92))
    notch_depth_in = max(0.0, tab_height_in)

    # If the notch width is too small or depth is ~0, treat as no tabs
    use_notch = bool(add_tabs and notch_width_in > 1e-4 and notch_depth_in > 1e-4)

    # ----------------------------
    # Build ribs
    # ----------------------------
    try:
        for i in range(rib_count):
            progress.progressValue = i
            adsk.doEvents()

            rib_occ = rib_occs.addNewComponent(adsk.core.Matrix3D.create())
            rib_comp = rib_occ.component
            rib_comp.name = f"Rib_{i+1:02d}"

            # Rib index placement coordinate (global across direction)
            idx_offset_in = i * pitch_in

            # Sketch on XY so we can make a curvy footprint; extrude in +Z for height
            sketch = rib_comp.sketches.add(rib_comp.xYConstructionPlane)
            curves = sketch.sketchCurves
            lines = curves.sketchLines
            splines = curves.sketchFittedSplines

            # Sample footprint centerline offsets along x
            x_vals = []
            y_center_vals = []

            for s in range(samples + 1):
                x_in = rib_length_in * (s / max(1, samples))
                x_vals.append(x_in)

                # Flow varies across ribs using idx_offset_in
                y_off = lateral_offset_in(x_in, idx_offset_in)

                # Local rib sketch is centered at y=0
                y_center_vals.append(y_off)

            # Smooth centerline offsets so the footprint is clean
            y_center_vals = smooth_series(y_center_vals, passes=smooth_passes)

            # Build top and bottom edge points (splines)
            half_th = rib_thickness_in * 0.5

            top_pts = adsk.core.ObjectCollection.create()
            bot_pts = adsk.core.ObjectCollection.create()

            for x_in, yc in zip(x_vals, y_center_vals):
                top_pts.add(adsk.core.Point3D.create(cm(x_in), cm(yc + half_th), 0))
            for x_in, yc in zip(reversed(x_vals), reversed(y_center_vals)):
                bot_pts.add(adsk.core.Point3D.create(cm(x_in), cm(yc - half_th), 0))

            top_spline = splines.add(top_pts)
            bot_spline = splines.add(bot_pts)

            # Endpoints for closing geometry
            # (SketchFittedSpline endpoints can be accessed from fit points we created)
            # We'll compute directly from our lists for robustness.
            x0 = x_vals[0]
            x1 = x_vals[-1]
            y_top_0 = y_center_vals[0] + half_th
            y_bot_0 = y_center_vals[0] - half_th
            y_top_1 = y_center_vals[-1] + half_th
            y_bot_1 = y_center_vals[-1] - half_th

            # BACK EDGE (x = rib_length_in): mostly straight with optional notch cut
            p_top_back = adsk.core.Point3D.create(cm(x1), cm(y_top_1), 0)
            p_bot_back = adsk.core.Point3D.create(cm(x1), cm(y_bot_1), 0)

            if use_notch:
                # Notch centered on local y=0
                y_n_top = notch_width_in * 0.5
                y_n_bot = -notch_width_in * 0.5
                x_notch_in = max(0.0, x1 - notch_depth_in)

                # Clamp notch extents to be inside the rib span between bottom and top at the back.
                # If the rib’s back ends are too narrow due to extreme flow offsets (rare), clip.
                y_n_top = min(y_n_top, max(y_bot_1, y_top_1))
                y_n_bot = max(y_n_bot, min(y_bot_1, y_top_1))

                # From top back down to top of notch
                p1 = adsk.core.Point3D.create(cm(x1), cm(y_n_top), 0)
                lines.addByTwoPoints(p_top_back, p1)

                # Into the notch (forward in -X)
                p2 = adsk.core.Point3D.create(cm(x_notch_in), cm(y_n_top), 0)
                lines.addByTwoPoints(p1, p2)

                # Down the notch interior
                p3 = adsk.core.Point3D.create(cm(x_notch_in), cm(y_n_bot), 0)
                lines.addByTwoPoints(p2, p3)

                # Back out to the back edge
                p4 = adsk.core.Point3D.create(cm(x1), cm(y_n_bot), 0)
                lines.addByTwoPoints(p3, p4)

                # Continue down to bottom back
                lines.addByTwoPoints(p4, p_bot_back)
            else:
                # Straight back edge
                lines.addByTwoPoints(p_top_back, p_bot_back)

            # FRONT EDGE (x = 0): make it curved (avoid a straight line)
            # We add a small 3-point spline bowing slightly inward.
            x_front_mid = min(rib_length_in * 0.03, 0.15)  # up to 0.15" bow depth
            p_front_bot = adsk.core.Point3D.create(cm(x0), cm(y_bot_0), 0)
            p_front_top = adsk.core.Point3D.create(cm(x0), cm(y_top_0), 0)
            p_front_mid = adsk.core.Point3D.create(cm(x_front_mid), cm(0.5 * (y_bot_0 + y_top_0)), 0)

            front_pts = adsk.core.ObjectCollection.create()
            front_pts.add(p_front_bot)
            front_pts.add(p_front_mid)
            front_pts.add(p_front_top)
            splines.add(front_pts)

            # Ensure profile exists
            if sketch.profiles.count == 0:
                ui.messageBox(
                    f"Profile failed on rib {i+1}.\n\n"
                    "Try:\n"
                    "- Reduce base_amplitude_in or flow_strength\n"
                    "- Increase smoothness or smooth_passes\n"
                    "- Increase samples\n"
                    "- Reduce tab notch depth/width"
                )
                return

            prof = sketch.profiles.item(0)

            # Extrude rib height along +Z
            extrudes = rib_comp.features.extrudeFeatures
            ext_in = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByString(f"{rib_height_in} in"))
            extrudes.add(ext_in)

            # Place rib occurrences in the container for preview layout
            m = adsk.core.Matrix3D.create()
            if layout_along_y:
                # Array direction is +Y
                m.translation = adsk.core.Vector3D.create(0, cm(idx_offset_in), 0)
            else:
                # Array direction is +X
                m.translation = adsk.core.Vector3D.create(cm(idx_offset_in), 0, 0)
            rib_occ.transform = m

    finally:
        progress.hide()

    # ----------------------------
    # Rotate whole container -90° about X axis
    # ----------------------------
    # This re-orients the generated sculpture for “real life” standing layout.
    rot = adsk.core.Matrix3D.create()
    rot.setToRotation(-math.pi / 2.0, adsk.core.Vector3D.create(1, 0, 0), adsk.core.Point3D.create(0, 0, 0))
    container_occ.transform = rot

    ui.messageBox(
        "Flow ribs generated (flowy footprint mode).\n\n"
        f"Seed: {seed}\n"
        f"Ribs: {rib_count}\n"
        f"Samples: {samples} | Smooth passes: {smooth_passes}\n"
        f"Flow angle (rad): {flow_angle_rad:.3f}\n"
        f"Tabs (back notch): {'ON' if use_notch else 'OFF'}\n"
        "Container rotated -90° about X."
    )
