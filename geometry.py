# geometry.py
# Surface-first heightfield + rib sketch/profile + tabs + extrusion + preview layout

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
    progress.show("OrganicFlowRibs", "Generating rib %v of %m", 0, rib_count, 0)

    # ----------------------------
    # Container component
    # ----------------------------
    container_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    container_comp = container_occ.component
    container_comp.name = f"{name_prefix}{rib_count}x_seed{seed}"
    rib_occs = container_comp.occurrences

    # Preview pitch: thickness + gap
    pitch_in = rib_thickness_in + gap_between_ribs_in
    total_y_in = (rib_count - 1) * pitch_in if rib_count > 1 else 0.0

    # Tabs
    tab_spans = build_tab_spans(tab_centers_in, tab_width_in, rib_length_in) if add_tabs else []

    # ----------------------------
    # Build a coherent 2D surface z = f(x,y)
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

    # Primary "dune" period (broad, reference-like)
    primary_period = max(bend_scale_in, rib_length_in * 1.25)

    # Secondary modulation (still broad)
    secondary_period = max(primary_period * 0.55, rib_length_in * 0.90)

    # Coherent phase drift across ribs (no per-rib phase jitter)
    # Stronger with wildness + flow_strength.
    y_phase_strength = (2.0 * math.pi) * (0.10 + 1.35 * wildness) * flow_strength * (0.25 + 0.75 * randomness)

    # Smooth low-frequency components for "terrain" richness
    comp_count = 2 + int(round(3 * detail))  # 2..5
    comp_count = max(2, min(5, comp_count))

    # Scale for these components
    u_scale = max(primary_period, rib_length_in)
    # v_scale should reflect sculpture depth; if only 1 rib, use a reasonable fallback
    v_scale = max(total_y_in if total_y_in > 0 else pitch_in, rib_length_in * 0.70)

    # Detail amplitude damped by smoothness (smoothness high => calmer)
    detail_amp = (
        base_amplitude_in
        * (0.08 + 0.38 * detail)
        * (0.25 + 0.75 * (1.0 - smoothness))
        * (0.30 + 0.70 * randomness)
    )

    components = []
    for k in range(1, comp_count + 1):
        fu = k
        fv = 1 if k <= 2 else 2  # keep v frequency low
        amp = detail_amp * master.uniform(-1.0, 1.0) * (1.0 / (k + 0.5))
        ph = master.uniform(0.0, 2.0 * math.pi)
        components.append((fu, fv, amp, ph))

    # Optional terrain mass: broad gaussian in (u,v), not centered
    if use_mass and rib_count > 1 and mass_strength > 0.0:
        # Bias the mass location to be somewhere "in frame"
        u0 = (0.10 + 0.80 * master.random()) * rot_u(rib_length_in, total_y_in if total_y_in > 0 else pitch_in)
        v0 = (0.15 + 0.70 * master.random()) * rot_v(rib_length_in, total_y_in if total_y_in > 0 else pitch_in)

        mass_u_sigma = max(rib_length_in * 0.35, bend_scale_in * 0.25)
        mass_v_sigma = max((total_y_in + pitch_in) * 0.35, rib_length_in * 0.25)

        mass_amp = base_amplitude_in * (0.10 + 0.55 * mass_strength) * (0.25 + 0.75 * randomness)
    else:
        u0 = v0 = mass_u_sigma = mass_v_sigma = mass_amp = 0.0

    # Stable secondary phase derived from seed
    phase2 = ((seed % 100000) / 100000.0) * (2.0 * math.pi)

    def end_envelope(x_in: float) -> float:
        """
        Smoothly fade to baseline at ends to avoid abrupt curvature.
        Higher smoothness => gentler fade.
        """
        t = max(0.0, min(1.0, x_in / rib_length_in))
        p = 2.0 + 1.2 * smoothness
        return math.pow(math.sin(math.pi * t), p)

    def height_at(x_in: float, y_in: float) -> float:
        """
        Returns Z profile height (0..rib_height) in inches, surface-first.
        """
        u = rot_u(x_in, y_in)
        v = rot_v(x_in, y_in)

        env = end_envelope(x_in)

        # y normalized -0.5..0.5 for coherent drift
        yt = 0.0 if total_y_in <= 0 else (y_in / total_y_in)
        yphase = y_phase_strength * (yt - 0.5)

        # Primary flowing bend (dominant)
        z = 0.0
        z += (base_amplitude_in * env) * math.sin((2.0 * math.pi * (u / primary_period)) + yphase)

        # Secondary gentle modulation
        z += (base_amplitude_in * env * 0.22 * (0.25 + 0.75 * randomness)) * math.sin(
            (2.0 * math.pi * (u / secondary_period)) + (0.65 * yphase) + phase2
        )

        # Low-frequency terrain components
        for (fu, fv, amp, ph) in components:
            z += env * amp * math.sin(
                (2.0 * math.pi * fu * (u / u_scale)) +
                (2.0 * math.pi * fv * (v / v_scale)) +
                ph
            )

        # Optional mass
        if use_mass and mass_amp != 0.0:
            du = (u - u0) / mass_u_sigma
            dv = (v - v0) / mass_v_sigma
            z += env * mass_amp * math.exp(-(du * du + dv * dv))

        # Clamp the signed surface signal
        z = max(-rib_height_in, min(rib_height_in, z))

        # Convert to a profile height (reference-like calmness)
        # Scaling 0.65 reduces extremes so it stays "gallery smooth".
        z_profile = rib_height_in - (z * 0.65)

        # Clamp to usable profile range
        return max(0.0, min(rib_height_in, z_profile))

    # ----------------------------
    # Build each rib as its own component inside the container
    # ----------------------------
    for i in range(rib_count):
        progress.progressValue = i
        adsk.doEvents()
        rib_occ = rib_occs.addNewComponent(adsk.core.Matrix3D.create())
        rib_comp = rib_occ.component
        rib_comp.name = f"Rib_{i+1:02d}"

        # Sketch on XZ plane so thickness extrudes along +Y
        sketch = rib_comp.sketches.add(rib_comp.xZConstructionPlane)
        curves = sketch.sketchCurves
        lines = curves.sketchLines
        splines = curves.sketchFittedSplines

        y_in = i * pitch_in

        # Sample profile
        x_vals = []
        z_vals = []
        for s in range(samples + 1):
            x_in = rib_length_in * (s / samples)
            x_vals.append(x_in)
            z_vals.append(height_at(x_in, y_in))

        # Smooth the sampled profile
        z_vals = smooth_series(z_vals, passes=smooth_passes)

        # Create spline using fit points
        fit_pts = adsk.core.ObjectCollection.create()
        for x_in, z_in in zip(x_vals, z_vals):
            fit_pts.add(adsk.core.Point3D.create(cm(x_in), cm(z_in), 0))

        splines.add(fit_pts)

        # Close profile:
        # Right vertical down to baseline
        x_right = rib_length_in
        z_right = z_vals[-1]
        lines.addByTwoPoints(
            adsk.core.Point3D.create(cm(x_right), cm(z_right), 0),
            adsk.core.Point3D.create(cm(x_right), cm(0.0), 0)
        )

        # Baseline leftwards, with optional tabs that dip down
        cur_x = rib_length_in
        baseline_z = 0.0
        tab_bottom_z = -tab_height_in

        p = adsk.core.Point3D.create(cm(cur_x), cm(baseline_z), 0)

        if add_tabs and len(tab_spans) > 0:
            # tab_spans are sorted right->left
            for (t0, t1) in tab_spans:
                # Move baseline from cur_x to t1
                if cur_x > t1:
                    p2 = adsk.core.Point3D.create(cm(t1), cm(baseline_z), 0)
                    lines.addByTwoPoints(p, p2)
                    p = p2
                    cur_x = t1

                # Down
                p2 = adsk.core.Point3D.create(cm(cur_x), cm(tab_bottom_z), 0)
                lines.addByTwoPoints(p, p2)
                p = p2

                # Left along bottom of tab
                p2 = adsk.core.Point3D.create(cm(t0), cm(tab_bottom_z), 0)
                lines.addByTwoPoints(p, p2)
                p = p2
                cur_x = t0

                # Up to baseline
                p2 = adsk.core.Point3D.create(cm(cur_x), cm(baseline_z), 0)
                lines.addByTwoPoints(p, p2)
                p = p2

            # Finish baseline to x=0
            if cur_x > 0.0:
                p2 = adsk.core.Point3D.create(cm(0.0), cm(baseline_z), 0)
                lines.addByTwoPoints(p, p2)
                p = p2
                cur_x = 0.0
        else:
            # Straight baseline
            p2 = adsk.core.Point3D.create(cm(0.0), cm(baseline_z), 0)
            lines.addByTwoPoints(p, p2)
            p = p2
            cur_x = 0.0

        # Left vertical up to start height (close)
        z_left = z_vals[0]
        lines.addByTwoPoints(
            adsk.core.Point3D.create(cm(0.0), cm(baseline_z), 0),
            adsk.core.Point3D.create(cm(0.0), cm(z_left), 0)
        )

        # Ensure we have a profile
        if sketch.profiles.count == 0:
            ui.messageBox(
                f"Profile failed on rib {i+1}.\n\n"
                "Try:\n"
                "- Lower Base amplitude / Detail\n"
                "- Increase Smoothness\n"
                "- Reduce Tab height/width\n"
                "- Increase samples (then keep smoothing passes modest)"
            )
            return

        prof = sketch.profiles.item(0)

        # Extrude thickness along +Y
        extrudes = rib_comp.features.extrudeFeatures
        ext_in = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ext_in.setDistanceExtent(False, adsk.core.ValueInput.createByString(f"{rib_thickness_in} in"))
        extrudes.add(ext_in)

        # Place ribs for preview layout
        m = adsk.core.Matrix3D.create()
        if layout_along_y:
            m.translation = adsk.core.Vector3D.create(0, cm(i * pitch_in), 0)
        else:
            m.translation = adsk.core.Vector3D.create(cm(i * pitch_in), 0, 0)
        rib_occ.transform = m
    progress.hide()
    
    ui.messageBox(
        "Flow ribs generated.\n\n"
        f"Seed: {seed}\n"
        f"Ribs: {rib_count}\n"
        f"Samples: {samples} | Smooth passes: {smooth_passes}\n"
        f"Flow angle (rad): {flow_angle_rad:.3f}"
    )
