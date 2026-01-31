__title__ = "Wavy Ribs Generator"
__description__ = "Generates wavy plywood ribs with optional tabs and wall-preview layout spacing"
__author__ = "Matthew"
__version__ = "3.0.0"

import adsk.core, adsk.fusion, traceback, math, re

# Keep handlers alive
_handlers = []

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        cmd_id = "wavyRibsGeneratorCmd"
        cmd_defs = ui.commandDefinitions
        existing = cmd_defs.itemById(cmd_id)
        if existing:
            existing.deleteMe()

        cmd_def = cmd_defs.addButtonDefinition(
            cmd_id,
            "Wavy Ribs Generator",
            "Generate wavy ribs with parameters"
        )

        on_created = CommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)

        cmd_def.execute()
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox("Failed:\n" + traceback.format_exc())


# ----------------------------
# Command Handlers
# ----------------------------
class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd = args.command
            inputs = cmd.commandInputs

            # --- Core rib dims ---
            inputs.addIntegerSpinnerCommandInput("ribCount", "Number of ribs", 1, 300, 1, 30)

            inputs.addValueInput("ribLength", "Rib length", "in",
                                 adsk.core.ValueInput.createByString("48 in"))
            inputs.addValueInput("ribHeight", "Rib height (max)", "in",
                                 adsk.core.ValueInput.createByString("4 in"))
            inputs.addValueInput("ribThickness", "Rib thickness", "in",
                                 adsk.core.ValueInput.createByString("0.75 in"))

            # --- Layout spacing (wall preview) ---
            inputs.addValueInput("gapBetweenRibs", "Gap between ribs (preview)", "in",
                                 adsk.core.ValueInput.createByString("1 in"))

            axis = inputs.addBoolValueInput("layoutAlongX", "Layout ribs along X (else Y)", True, "", False)
            axis.tooltip = "OFF = stack along Y (depth). ON = spread left-right along X."

            # --- Wave controls ---
            inputs.addValueInput("waveAmp", "Wave amplitude", "in",
                                 adsk.core.ValueInput.createByString("1.25 in"))
            inputs.addValueInput("wavePeriod", "Wave period", "in",
                                 adsk.core.ValueInput.createByString("24 in"))

            inputs.addIntegerSpinnerCommandInput("samples", "Spline smoothness (samples)", 20, 400, 10, 180)
            inputs.addValueInput("totalPhase", "Total phase across ribs (degrees)", "deg",
                                 adsk.core.ValueInput.createByString("180 deg"))

            # --- Tabs ---
            tabs = inputs.addBoolValueInput("addTabs", "Add tabs (2D tenons)", True, "", True)
            tabs.tooltip = "Tabs are drawn as part of the rib profile, sticking DOWN below baseline."

            inputs.addValueInput("tabWidth", "Tab width", "in",
                                 adsk.core.ValueInput.createByString("4 in"))
            inputs.addValueInput("tabHeight", "Tab height", "in",
                                 adsk.core.ValueInput.createByString("0.675 in"))

            # comma-separated tab centers
            tab_centers = inputs.addStringValueInput("tabCenters", "Tab centers (in, comma-separated)", "16,32")
            tab_centers.tooltip = "Example: 16,32 will place two tabs centered at 16\" and 32\" along the rib length."

            # --- Execute handler ---
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

            # Fusion value inputs return internal units (cm/rad) in .value
            # Convert cm -> inches by /2.54
            def inches(val_input_id: str) -> float:
                return inputs.itemById(val_input_id).value / 2.54

            def degrees(val_input_id: str) -> float:
                # Fusion "deg" value input still returns radians internally
                # so convert rad -> deg
                return inputs.itemById(val_input_id).value * (180.0 / math.pi)

            rib_count = inputs.itemById("ribCount").value
            rib_length_in = inches("ribLength")
            rib_height_in = inches("ribHeight")
            rib_thickness_in = inches("ribThickness")
            gap_between_ribs_in = inches("gapBetweenRibs")

            wave_amp_in = inches("waveAmp")
            wave_period_in = inches("wavePeriod")

            samples = inputs.itemById("samples").value
            total_phase_deg = degrees("totalPhase")

            add_tabs = inputs.itemById("addTabs").value
            tab_width_in = inches("tabWidth")
            tab_height_in = inches("tabHeight")
            tab_centers_raw = inputs.itemById("tabCenters").value

            layout_along_x = inputs.itemById("layoutAlongX").value

            # Basic validation with gentle clamping
            if rib_length_in <= 0 or rib_height_in <= 0 or rib_thickness_in <= 0:
                ui.messageBox("Rib dimensions must be > 0.")
                return

            if wave_period_in <= 0:
                ui.messageBox("Wave period must be > 0.")
                return

            if samples < 20:
                samples = 20

            # If amplitude > height, clamp it so profile doesn't invert constantly
            if wave_amp_in > rib_height_in:
                wave_amp_in = rib_height_in

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

            # Generate ribs
            generate_wavy_ribs(
                root=root,
                rib_count=rib_count,
                rib_length_in=rib_length_in,
                rib_height_in=rib_height_in,
                rib_thickness_in=rib_thickness_in,
                gap_between_ribs_in=gap_between_ribs_in,
                wave_amp_in=wave_amp_in,
                wave_period_in=wave_period_in,
                samples=samples,
                total_phase_deg=total_phase_deg,
                add_tabs=add_tabs,
                tab_width_in=tab_width_in,
                tab_height_in=tab_height_in,
                tab_centers_in=tab_centers_in,
                layout_along_x=layout_along_x
            )

        except:
            if ui:
                ui.messageBox("Failed:\n" + traceback.format_exc())


class CommandDestroyHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        # Let Fusion terminate the script when the command is done/closed
        adsk.terminate()

# ----------------------------
# Geometry Generator
# ----------------------------
def generate_wavy_ribs(root,
                       rib_count: int,
                       rib_length_in: float,
                       rib_height_in: float,
                       rib_thickness_in: float,
                       gap_between_ribs_in: float,
                       wave_amp_in: float,
                       wave_period_in: float,
                       samples: int,
                       total_phase_deg: float,
                       add_tabs: bool,
                       tab_width_in: float,
                       tab_height_in: float,
                       tab_centers_in,
                       layout_along_x: bool):

    ui = adsk.core.Application.get().userInterface

    def cm(v): return v * 2.54
    def deg2rad(d): return d * math.pi / 180.0

    def wave_height_in(x_in, phase_deg):
        # top edge oscillates but clamped into [0, rib_height_in]
        z = rib_height_in - (wave_amp_in * math.sin((2.0 * math.pi * x_in / wave_period_in) + deg2rad(phase_deg)))
        return max(0.0, min(rib_height_in, z))

    # Container component
    container_occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    container_comp = container_occ.component
    container_comp.name = f"WavyRibs_{rib_count}x"
    occs = container_comp.occurrences

    # Preview spacing pitch
    pitch_in = rib_thickness_in + gap_between_ribs_in

    # Tab spans (x0, x1) sorted right->left
    tab_spans = []
    if add_tabs:
        for c in tab_centers_in:
            x0 = max(0.0, c - tab_width_in / 2.0)
            x1 = min(rib_length_in, c + tab_width_in / 2.0)
            if x1 > x0:
                tab_spans.append((x0, x1))
        tab_spans.sort(key=lambda t: t[0], reverse=True)

    for i in range(rib_count):
        phase = 0.0 if rib_count == 1 else (i / (rib_count - 1)) * total_phase_deg

        rib_occ = occs.addNewComponent(adsk.core.Matrix3D.create())
        rib_comp = rib_occ.component
        rib_comp.name = f"Rib_{i+1:02d}"

        # Sketch on XZ: X=length, Z=height (tabs go negative Z)
        sk = rib_comp.sketches.add(rib_comp.xZConstructionPlane)
        curves = sk.sketchCurves
        lines = curves.sketchLines
        splines = curves.sketchFittedSplines

        # Top spline points
        fitPts = adsk.core.ObjectCollection.create()
        for s in range(samples + 1):
            x_in = rib_length_in * s / samples
            z_in = wave_height_in(x_in, phase)
            fitPts.add(adsk.core.Point3D.create(cm(x_in), cm(z_in), 0))

        splines.add(fitPts)

        # Right vertical down to baseline
        x_right = rib_length_in
        z_right_in = fitPts.item(fitPts.count - 1).y / 2.54
        lines.addByTwoPoints(
            adsk.core.Point3D.create(cm(x_right), cm(z_right_in), 0),
            adsk.core.Point3D.create(cm(x_right), cm(0.0), 0)
        )

        # Bottom edge with tabs from right -> left
        cur_x = rib_length_in
        baseline_z = 0.0
        tab_bottom_z = -tab_height_in

        p = adsk.core.Point3D.create(cm(cur_x), cm(baseline_z), 0)

        if add_tabs and len(tab_spans) > 0:
            for (t0, t1) in tab_spans:
                # Baseline to tab right edge
                if cur_x > t1:
                    p2 = adsk.core.Point3D.create(cm(t1), cm(baseline_z), 0)
                    lines.addByTwoPoints(p, p2)
                    p = p2
                    cur_x = t1

                # Down
                p2 = adsk.core.Point3D.create(cm(cur_x), cm(tab_bottom_z), 0)
                lines.addByTwoPoints(p, p2)
                p = p2

                # Left along bottom
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
            # Straight baseline to x=0
            p2 = adsk.core.Point3D.create(cm(0.0), cm(baseline_z), 0)
            lines.addByTwoPoints(p, p2)
            p = p2
            cur_x = 0.0

        # Left vertical up to start of spline
        z_left_in = fitPts.item(0).y / 2.54
        lines.addByTwoPoints(
            adsk.core.Point3D.create(cm(0.0), cm(baseline_z), 0),
            adsk.core.Point3D.create(cm(0.0), cm(z_left_in), 0)
        )

        if sk.profiles.count == 0:
            ui.messageBox(f"Profile failed on rib {i+1}. Try lowering wave_amp or tab height.")
            return

        prof = sk.profiles.item(0)

        # Extrude thickness in +Y (depth off the wall)
        ext = rib_comp.features.extrudeFeatures
        ei = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        ei.setDistanceExtent(False, adsk.core.ValueInput.createByString(f"{rib_thickness_in} in"))
        ext.add(ei)

        # Placement (wall preview)
        m = adsk.core.Matrix3D.create()
        if layout_along_x:
            m.translation = adsk.core.Vector3D.create(cm(i * pitch_in), 0, 0)
        else:
            m.translation = adsk.core.Vector3D.create(0, cm(i * pitch_in), 0)

        # 2) flip 180° so "down" becomes down (tabs end up at the bottom)
        flip = adsk.core.Matrix3D.create()
        flip.setToRotation(math.pi, adsk.core.Vector3D.create(1, 0, 0), adsk.core.Point3D.create(0, 0, 0))

        m.transformBy(flip)

        rib_occ.transform = m

    ui.messageBox(
        "Done.\n\n"
        f"Ribs: {rib_count}\n"
        f"Size: {rib_length_in:.2f}\" x {rib_height_in:.2f}\" x {rib_thickness_in:.2f}\"\n"
        f"Preview gap: {gap_between_ribs_in:.2f}\" (pitch {pitch_in:.2f}\")\n"
        f"Tabs: {'ON' if add_tabs else 'OFF'}"
    )
