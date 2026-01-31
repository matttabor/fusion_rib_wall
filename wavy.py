__title__ = "Organic Wavy Ribs (Seeded)"
__description__ = "Generates wavy plywood ribs with dune/topography randomness, seeded repeatability, and optional tabs"
__author__ = "Matthew"
__version__ = "4.0.0"

import adsk.core, adsk.fusion, traceback, math, random, re

_handlers = []

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        cmd_id = "organicWavyRibsSeededCmd"
        cmd_defs = ui.commandDefinitions
        existing = cmd_defs.itemById(cmd_id)
        if existing:
            existing.deleteMe()

        cmd_def = cmd_defs.addButtonDefinition(
            cmd_id,
            "Organic Wavy Ribs (Seeded)",
            "Generate wavy ribs with seeded organic randomness"
        )

        on_created = CommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)

        cmd_def.execute()
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox("Failed:\n" + traceback.format_exc())


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd = args.command
            inputs = cmd.commandInputs

            # --- Core dims ---
            inputs.addIntegerSpinnerCommandInput("ribCount", "Number of ribs", 1, 400, 1, 30)
            inputs.addValueInput("ribLength", "Rib length", "in", adsk.core.ValueInput.createByString("48 in"))
            inputs.addValueInput("ribHeight", "Rib height (max)", "in", adsk.core.ValueInput.createByString("4 in"))
            inputs.addValueInput("ribThickness", "Rib thickness", "in", adsk.core.ValueInput.createByString("0.75 in"))
            inputs.addValueInput("gapBetweenRibs", "Gap between ribs (preview)", "in", adsk.core.ValueInput.createByString("1 in"))

            # Preview layout axis
            inputs.addBoolValueInput("layoutAlongY", "Layout along Y (like stacked sculpture)", True, "", True)

            # --- Seed + style controls ---
            inputs.addIntegerSpinnerCommandInput("seed", "Seed (signed int)", -2147483648, 2147483647, 1, 12345)

            # The two vibes you picked: 1) organic dune + 2) topography. We'll blend via these knobs.
            inputs.addValueInput("randomness", "Randomness (0-1)", "", adsk.core.ValueInput.createByString("0.45"))
            
            wild = inputs.addValueInput("wildness", "Wildness (0–1)", "",
                            adsk.core.ValueInput.createByString("0.35"))
            wild.tooltip = "How dramatic the surface flow becomes"
            wild.tooltipDescription = (
                "Controls large-scale directional sweeps across ribs.\n\n"
                "Low values = gentle dune-like flow\n"
                "High values = ridges can start in corners and sweep diagonally\n\n"
                "Does not add noise—only large, smooth motion."
            )

            smooth = inputs.addValueInput("smoothness", "Smoothness (0–1)", "",
                              adsk.core.ValueInput.createByString("0.65"))
            smooth.tooltip = "Bias toward smooth vs varied forms"
            smooth.tooltipDescription = (
                "Controls how evenly curvature changes.\n\n"
                "Higher = calmer, flowing shapes\n"
                "Lower = more hand-carved, topographic feel\n\n"
                "This affects warp strength and frequency internally."
            )

            # --- Wave base parameters ---
            inputs.addValueInput("waveAmp", "Base amplitude", "in", adsk.core.ValueInput.createByString("1.25 in"))
            inputs.addValueInput("wavePeriod", "Base period", "in", adsk.core.ValueInput.createByString("24 in"))

            # --- Variation knobs ---
            ampv = inputs.addValueInput("ampVar", "Amplitude variation (0–1)", "",
                            adsk.core.ValueInput.createByString("0.25"))
            ampv.tooltip = "Vary wave height between ribs"
            ampv.tooltipDescription = (
                "Randomly changes the height of the wave per rib.\n\n"
                "Low values = consistent height\n"
                "Higher values = more organic rise and fall\n\n"
                "Automatically clamped so ribs never exceed max height."
            )

            perv = inputs.addValueInput("perVar", "Period variation (0–1)", "",
                            adsk.core.ValueInput.createByString("0.30"))
            perv.tooltip = "Vary wavelength between ribs"
            perv.tooltipDescription = (
                "Randomly stretches or compresses the wave period per rib.\n\n"
                "Low values keep crests aligned.\n"
                "Higher values make spacing between ridges less uniform.\n\n"
                "Very effective for breaking the 'same curve shifted' look."
            )

            phase = inputs.addValueInput(
                "phaseJitter",
                "Phase jitter (0–1)",
                "",
                adsk.core.ValueInput.createByString("0.25")
            )

            phase.tooltip = "Offsets the wave phase per rib"
            phase.tooltipDescription = (
                "Adds a small random phase offset to each rib's wave.\n\n"
                "Low values keep ribs aligned.\n"
                "Higher values break alignment so ridges drift and sweep diagonally.\n\n"
                "Best range: 0.15-0.4"
            )

            # --- Warp field along length (low frequency) ---
            warp = inputs.addValueInput("warpStrength", "Warp strength", "in",
                            adsk.core.ValueInput.createByString("0.75 in"))
            warp.tooltip = "Bends the wave along its length"
            warp.tooltipDescription = (
                "Applies a smooth, low-frequency warp along the rib length.\n\n"
                "This breaks uniform spacing without adding jitter.\n\n"
                "Higher values make ridges wander more dramatically."
            )

            inputs.addIntegerSpinnerCommandInput("warpWaves", "Warp waves (1-6)", 1, 6, 1, 3)
            

            # --- End fade to prevent abrupt curvature at ends ---
            fade = inputs.addBoolValueInput("useEndFade", "Use end-fade envelope", True, "", True)
            fade.tooltip = "Smooths wave to zero at ends"
            fade.tooltipDescription = (
                "Fades wave amplitude to zero near the rib ends.\n\n"
                "Prevents abrupt curvature starts/stops and creates a finished edge.\n\n"
                "Strongly recommended for wall-mounted pieces."
            )

            fp = inputs.addValueInput("fadePower", "End-fade power (1-4)", "",
                           adsk.core.ValueInput.createByString("2.2"))
            fp.tooltip = "Controls how quickly the wave fades at the ends"
            fp.tooltipDescription = (
                "Higher values keep the wave strong until closer to the edge.\n"
                "Lower values fade more gradually.\n\n"
                "Typical range: 1.8-2.8"
            )

            # --- “Bulge” / topography feature (makes it feel hand-carved) ---
            inputs.addBoolValueInput("useBulge", "Add topography bulge", True, "", True)
            inputs.addValueInput("bulgeStrength", "Bulge strength (0-1)", "", adsk.core.ValueInput.createByString("0.35"))

            # --- Spline resolution ---
            inputs.addIntegerSpinnerCommandInput("samples", "Spline samples (smoothness)", 40, 500, 10, 220)

            # --- Tabs ---
            tabs = inputs.addBoolValueInput("addTabs", "Add tabs (2D tenons)", True, "", True)
            inputs.addValueInput("tabWidth", "Tab width", "in", adsk.core.ValueInput.createByString("4 in"))
            inputs.addValueInput("tabHeight", "Tab height", "in", adsk.core.ValueInput.createByString("0.675 in"))
            inputs.addStringValueInput("tabCenters", "Tab centers (in, comma-separated)", "16,32")

            # --- Housekeeping: delete old containers ---
            inputs.addBoolValueInput("deleteOld", "Delete previous 'OrganicRibs_*' containers", True, "", True)

            on_execute = CommandExecuteHandler()
            cmd.execute.add(on_execute)
            _handlers.append(on_execute)

            on_destroy = CommandDestroyHandler()
            cmd.destroy.add(on_destroy)
            _handlers.append(on_destroy)

        except:
            adsk.core.Application.get().userInterface.messageBox("Failed:\n" + traceback.format_exc())


class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        ui = None
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface
            design = adsk.fusion.Design.cast(app.activeProduct)
            if not design:
                ui.messageBox("No active Fusion design.")
                return

            root = design.rootComponent
            inputs = args.command.commandInputs

            # Value inputs: .value returns internal units (cm for lengths; raw for unitless; radians for angles if any)
            def inches(id_): return inputs.itemById(id_).value / 2.54
            def unitless(id_): return float(inputs.itemById(id_).value)

            rib_count = inputs.itemById("ribCount").value
            rib_length_in = inches("ribLength")
            rib_height_in = inches("ribHeight")
            rib_thickness_in = inches("ribThickness")
            gap_between_ribs_in = inches("gapBetweenRibs")
            layout_along_y = inputs.itemById("layoutAlongY").value

            seed = inputs.itemById("seed").value

            randomness = clamp01(unitless("randomness"))
            wildness = clamp01(unitless("wildness"))
            smoothness = clamp01(unitless("smoothness"))

            base_amp_in = inches("waveAmp")
            base_period_in = inches("wavePeriod")

            amp_var = clamp01(unitless("ampVar"))
            per_var = clamp01(unitless("perVar"))
            phase_jitter = clamp01(unitless("phaseJitter"))

            warp_strength_in = inches("warpStrength")
            warp_waves = inputs.itemById("warpWaves").value

            use_end_fade = inputs.itemById("useEndFade").value
            fade_power = max(1.0, min(4.0, unitless("fadePower")))

            use_bulge = inputs.itemById("useBulge").value
            bulge_strength = clamp01(unitless("bulgeStrength"))

            samples = inputs.itemById("samples").value

            add_tabs = inputs.itemById("addTabs").value
            tab_width_in = inches("tabWidth")
            tab_height_in = inches("tabHeight")
            tab_centers_raw = inputs.itemById("tabCenters").value

            delete_old = inputs.itemById("deleteOld").value

            # Basic validation
            if rib_length_in <= 0 or rib_height_in <= 0 or rib_thickness_in <= 0:
                ui.messageBox("Rib dimensions must be > 0.")
                return
            if base_period_in <= 0:
                ui.messageBox("Base period must be > 0.")
                return
            if samples < 40:
                samples = 40

            # Clamp amplitude to height (we also envelope it, but keep sane)
            base_amp_in = min(base_amp_in, rib_height_in)

            tab_centers_in = []
            if add_tabs:
                try:
                    parts = [p.strip() for p in tab_centers_raw.split(",") if p.strip()]
                    for p in parts:
                        tab_centers_in.append(float(p))
                except:
                    ui.messageBox("Could not parse tab centers. Use format like: 16,32")
                    return
                if len(tab_centers_in) == 0:
                    tab_centers_in = [16.0, 32.0]

            if delete_old:
                delete_containers_with_prefix(root, "OrganicRibs_")

            generate_organic_ribs(
                root=root,
                seed=seed,
                rib_count=rib_count,
                rib_length_in=rib_length_in,
                rib_height_in=rib_height_in,
                rib_thickness_in=rib_thickness_in,
                gap_between_ribs_in=gap_between_ribs_in,
                layout_along_y=layout_along_y,

                randomness=randomness,
                wildness=wildness,
                smoothness=smoothness,

                base_amp_in=base_amp_in,
                base_period_in=base_period_in,
                amp_var=amp_var,
                per_var=per_var,
                phase_jitter=phase_jitter,

                warp_strength_in=warp_strength_in,
                warp_waves=warp_waves,

                use_end_fade=use_end_fade,
                fade_power=fade_power,

                use_bulge=use_bulge,
                bulge_strength=bulge_strength,

                samples=samples,

                add_tabs=add_tabs,
                tab_width_in=tab_width_in,
                tab_height_in=tab_height_in,
                tab_centers_in=tab_centers_in
            )

        except:
            if ui:
                ui.messageBox("Failed:\n" + traceback.format_exc())


class CommandDestroyHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        adsk.terminate()


# ----------------------------
# Helpers
# ----------------------------

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))

def delete_containers_with_prefix(root: adsk.fusion.Component, prefix: str):
    # Deletes occurrences at the root whose component name starts with prefix
    # (keeps your model from accumulating previous runs)
    occs = root.occurrences
    to_delete = []
    for o in occs:
        try:
            if o.component and o.component.name.startswith(prefix):
                to_delete.append(o)
        except:
            pass
    for o in to_delete:
        try:
            o.deleteMe()
        except:
            pass


# ----------------------------
# Generator
# ----------------------------

def generate_organic_ribs(
    root,
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

    base_amp_in: float,
    base_period_in: float,
    amp_var: float,
    per_var: float,
    phase_jitter: float,

    warp_strength_in: float,
    warp_waves: int,

    use_end_fade: bool,
    fade_power: float,

    use_bulge: bool,
    bulge_strength: float,

    samples: int,

    add_tabs: bool,
    tab_width_in: float,
    tab_height_in: float,
    tab_centers_in
):
    ui = adsk.core.Application.get().userInterface

    def cm(v): return v * 2.54

    # Master RNG for repeatability
    master = random.Random(seed)

    # Container component
    container_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    container_comp = container_occ.component
    container_comp.name = f"OrganicRibs_{rib_count}x_seed{seed}"
    occs = container_comp.occurrences

    pitch_in = rib_thickness_in + gap_between_ribs_in

    # Precompute tab spans (x0, x1) sorted right->left
    tab_spans = []
    if add_tabs:
        for c in tab_centers_in:
            x0 = max(0.0, c - tab_width_in / 2.0)
            x1 = min(rib_length_in, c + tab_width_in / 2.0)
            if x1 > x0:
                tab_spans.append((x0, x1))
        tab_spans.sort(key=lambda t: t[0], reverse=True)

    # Bulge profile across ribs (topography feel)
    # We pick a seeded center and sigma so it doesn't always bulge dead center.
    if rib_count > 1:
        center = (rib_count - 1) * (0.35 + 0.30 * master.random())  # 0.35..0.65
    else:
        center = 0.0
    sigma = max(1.0, rib_count * (0.14 + 0.10 * master.random()))   # 0.14..0.24 of rib_count

    # A diagonal “corner sweep” phase strength (radians), scaled by wildness
    # This couples rib index and x so ridges can slant across the sculpture.
    diag_strength = (2.0 * math.pi) * (0.5 + 4.0 * wildness) * (0.25 + 0.75 * randomness)

    # Global x-warp components for coherence (shared across ribs)
    global_warp_components = []
    gw = max(1, min(6, warp_waves))
    # Make warp smoother when smoothness is high
    global_warp_scale = warp_strength_in * (0.35 + 0.65 * (1.0 - smoothness))  # less warp at high smoothness
    for k in range(1, gw + 1):
        amp = global_warp_scale * (master.uniform(-1.0, 1.0)) * (1.0 / k)
        ph = master.uniform(0.0, 2.0 * math.pi)
        global_warp_components.append((k, amp, ph))

    def envelope(x_in: float, rib_rng: random.Random) -> float:
        if not use_end_fade:
            return 1.0

        # Add a little per-rib variation so sometimes the fade "starts in a corner"
        # but keep it smooth and deterministic.
        # shift in [-0.08, +0.08] of length (scaled by wildness+randomness)
        shift = (rib_rng.uniform(-0.08, 0.08)) * (wildness * 0.7 + randomness * 0.3)
        t = (x_in / rib_length_in) + shift

        # Clamp to [0,1]
        t = max(0.0, min(1.0, t))

        # sin(pi*t)^p goes to 0 at ends, smooth interior
        return math.pow(math.sin(math.pi * t), fade_power)

    def warp_x(x_in: float, rib_rng: random.Random) -> float:
        # Low-frequency warp. No jitter, CNC friendly.
        # Blend global (coherent) + per-rib (individual) warps.
        w = 0.0

        # Global components
        for (k, amp, ph) in global_warp_components:
            w += amp * math.sin((2.0 * math.pi * k * x_in / rib_length_in) + ph)

        # Per-rib components (smaller, controlled)
        local_scale = warp_strength_in * (0.25 + 0.75 * randomness) * (0.60 + 0.40 * (1.0 - smoothness))
        local_waves = max(1, min(6, warp_waves))
        for k in range(1, local_waves + 1):
            amp = local_scale * rib_rng.uniform(-1.0, 1.0) * (1.0 / (k + 1))
            ph = rib_rng.uniform(0.0, 2.0 * math.pi)
            # one evaluation per x would be expensive to randomize per point
            # so we instead build deterministic components per rib by seeding once:
            # We'll store them in rib data.
            # (handled by precomputed rib components below)
            pass

        return w

    # Precompute per-rib random parameters and local warp components (deterministic)
    rib_params = []
    for i in range(rib_count):
        rib_rng = random.Random(seed + i * 10007)

        # Amplitude & period drift
        Ai = base_amp_in * (1.0 + (amp_var * randomness) * rib_rng.uniform(-1.0, 1.0))
        Pi = base_period_in * (1.0 + (per_var * randomness) * rib_rng.uniform(-1.0, 1.0))
        Pi = max(3.0, Pi)  # prevent silly small periods

        # Phase baseline + jitter
        phi0 = rib_rng.uniform(0.0, 2.0 * math.pi) * (phase_jitter * randomness)

        # Bulge factor across ribs (topography feel)
        bulge = 1.0
        if use_bulge and rib_count > 1:
            d = (i - center) / sigma
            bulge = 1.0 + bulge_strength * randomness * math.exp(-(d * d))

        # Local warp components for this rib
        local_components = []
        local_waves = max(1, min(6, warp_waves))
        local_scale = warp_strength_in * (0.25 + 0.75 * randomness) * (0.60 + 0.40 * (1.0 - smoothness))
        for k in range(1, local_waves + 1):
            amp = local_scale * rib_rng.uniform(-1.0, 1.0) * (1.0 / (k + 1))
            ph = rib_rng.uniform(0.0, 2.0 * math.pi)
            local_components.append((k, amp, ph))

        rib_params.append((Ai, Pi, phi0, bulge, local_components))

    def warp_total(x_in: float, local_components) -> float:
        # Combine global + local warp smoothly
        w = 0.0
        for (k, amp, ph) in global_warp_components:
            w += amp * math.sin((2.0 * math.pi * k * x_in / rib_length_in) + ph)
        for (k, amp, ph) in local_components:
            w += amp * math.sin((2.0 * math.pi * k * x_in / rib_length_in) + ph)
        return w

    # Build ribs
    for i in range(rib_count):
        rib_occ = occs.addNewComponent(adsk.core.Matrix3D.create())
        rib_comp = rib_occ.component
        rib_comp.name = f"Rib_{i+1:02d}"

        # Sketch on XZ plane
        sk = rib_comp.sketches.add(rib_comp.xZConstructionPlane)
        curves = sk.sketchCurves
        lines = curves.sketchLines
        splines = curves.sketchFittedSplines

        rib_rng = random.Random(seed + i * 10007)
        Ai, Pi, phi0, bulge, local_components = rib_params[i]

        # A rib index normalized 0..1 (used for diagonal sweep)
        rib_t = 0.0 if rib_count == 1 else (i / (rib_count - 1))

        fitPts = adsk.core.ObjectCollection.create()
        for s in range(samples + 1):
            x_in = rib_length_in * s / samples

            env = envelope(x_in, rib_rng)

            # Warp x to break uniformity
            w = warp_total(x_in, local_components)

            # Diagonal / corner sweep term:
            # This couples rib index and x. As wildness rises, ridges slant more.
            diag = diag_strength * (rib_t - 0.5) * (x_in / rib_length_in)

            # Main height
            z = rib_height_in - (env * (Ai * bulge)) * math.sin((2.0 * math.pi * (x_in + w) / Pi) + phi0 + diag)

            # Clamp into [0, rib_height_in]
            z = max(0.0, min(rib_height_in, z))

            fitPts.add(adsk.core.Point3D.create(cm(x_in), cm(z), 0))

        splines.add(fitPts)

        # Close profile down to baseline Z=0 with optional tabs to negative Z
        x_right = rib_length_in
        z_right_in = fitPts.item(fitPts.count - 1).y / 2.54
        lines.addByTwoPoints(
            adsk.core.Point3D.create(cm(x_right), cm(z_right_in), 0),
            adsk.core.Point3D.create(cm(x_right), cm(0.0), 0)
        )

        cur_x = rib_length_in
        baseline_z = 0.0
        tab_bottom_z = -tab_height_in

        p = adsk.core.Point3D.create(cm(cur_x), cm(baseline_z), 0)

        if add_tabs and len(tab_spans) > 0:
            for (t0, t1) in tab_spans:
                if cur_x > t1:
                    p2 = adsk.core.Point3D.create(cm(t1), cm(baseline_z), 0)
                    lines.addByTwoPoints(p, p2)
                    p = p2
                    cur_x = t1

                # Down
                p2 = adsk.core.Point3D.create(cm(cur_x), cm(tab_bottom_z), 0)
                lines.addByTwoPoints(p, p2)
                p = p2

                # Left
                p2 = adsk.core.Point3D.create(cm(t0), cm(tab_bottom_z), 0)
                lines.addByTwoPoints(p, p2)
                p = p2
                cur_x = t0

                # Up
                p2 = adsk.core.Point3D.create(cm(cur_x), cm(baseline_z), 0)
                lines.addByTwoPoints(p, p2)
                p = p2

            if cur_x > 0.0:
                p2 = adsk.core.Point3D.create(cm(0.0), cm(baseline_z), 0)
                lines.addByTwoPoints(p, p2)
                p = p2
                cur_x = 0.0
        else:
            p2 = adsk.core.Point3D.create(cm(0.0), cm(baseline_z), 0)
            lines.addByTwoPoints(p, p2)
            p = p2
            cur_x = 0.0

        z_left_in = fitPts.item(0).y / 2.54
        lines.addByTwoPoints(
            adsk.core.Point3D.create(cm(0.0), cm(baseline_z), 0),
            adsk.core.Point3D.create(cm(0.0), cm(z_left_in), 0)
        )

        if sk.profiles.count == 0:
            ui.messageBox(f"Profile failed on rib {i+1}. Try lowering amplitude/warp or tab height.")
            return

        prof = sk.profiles.item(0)

        # Extrude thickness along +Y
        ext = rib_comp.features.extrudeFeatures
        ei = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ei.setDistanceExtent(False, adsk.core.ValueInput.createByString(f"{rib_thickness_in} in"))
        ext.add(ei)

        # Placement
        m = adsk.core.Matrix3D.create()
        if layout_along_y:
            m.translation = adsk.core.Vector3D.create(0, cm(i * pitch_in), 0)
        else:
            m.translation = adsk.core.Vector3D.create(cm(i * pitch_in), 0, 0)
        rib_occ.transform = m

    ui.messageBox(
        "Organic ribs generated.\n\n"
        f"Seed: {seed}\n"
        f"Ribs: {rib_count}\n"
        f"Randomness: {randomness:.2f} | Wildness: {wildness:.2f} | Smoothness: {smoothness:.2f}\n"
        f"End-fade: {'ON' if use_end_fade else 'OFF'} | Bulge: {'ON' if use_bulge else 'OFF'}"
    )
