# generator.py
# Reads dialog inputs and generates the model by calling geometry.py

import adsk.core
import adsk.fusion
import traceback

import geometry


def _val_in(inputs, input_id: str) -> float:
    """
    Reads a ValueInput stored as internal units (cm in Fusion).
    Returns value in inches.
    """
    v = inputs.itemById(input_id).value  # internal length units (cm)
    return float(v) / 2.54


def _val_num(inputs, input_id: str) -> float:
    """Reads a unitless ValueInput (0–1 sliders etc.)."""
    return float(inputs.itemById(input_id).value)


def _int(inputs, input_id: str) -> int:
    return int(inputs.itemById(input_id).value)


def _bool(inputs, input_id: str) -> bool:
    return bool(inputs.itemById(input_id).value)


def _parse_csv_floats(text: str):
    out = []
    for part in (text or "").split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    return out


def execute(args):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        cmd = args.command
        inputs = cmd.commandInputs

        # --- Read MAIN ---
        rib_count = _int(inputs, "ribCount")
        rib_length_in = _val_in(inputs, "ribLength")
        rib_height_in = _val_in(inputs, "ribHeight")
        rib_thickness_in = _val_in(inputs, "ribThickness")
        gap_between_ribs_in = _val_in(inputs, "gapBetweenRibs")
        layout_along_y = _bool(inputs, "layoutAlongY")

        # --- Read FLOW ---
        seed = _int(inputs, "seed")
        randomness = _val_num(inputs, "randomness")
        wildness = _val_num(inputs, "wildness")
        smoothness = _val_num(inputs, "smoothness")

        base_amplitude_in = _val_in(inputs, "baseAmplitude")
        bend_scale_in = _val_in(inputs, "bendScale")
        flow_angle_deg = float(inputs.itemById("flowAngleDeg").value)  # angle input (deg internal)
        flow_strength = _val_num(inputs, "flowStrength")
        detail = _val_num(inputs, "detail")

        use_mass = _bool(inputs, "useMass")
        mass_strength = _val_num(inputs, "massStrength")

        # --- Read QUALITY ---
        samples = _int(inputs, "samples")
        smooth_passes = _int(inputs, "smoothPasses")

        # --- Read TABS ---
        add_tabs = _bool(inputs, "addTabs")
        tab_width_in = _val_in(inputs, "tabWidth")
        tab_height_in = _val_in(inputs, "tabHeight")
        tab_centers_in = _parse_csv_floats(inputs.itemById("tabCenters").value)

        # --- Housekeeping ---
        delete_old = _bool(inputs, "deleteOld")

        ui.messageBox("Starting geometry… ✅")

        # Call into geometry.py
        # IMPORTANT: your geometry.py needs to provide a function with this signature.
        # If your function name differs, we'll adjust after you paste geometry.py.
        geometry.generate(
            rib_count=rib_count,
            rib_length_in=rib_length_in,
            rib_height_in=rib_height_in,
            rib_thickness_in=rib_thickness_in,
            gap_between_ribs_in=gap_between_ribs_in,
            layout_along_y=layout_along_y,
            seed=seed,
            randomness=randomness,
            wildness=wildness,
            smoothness=smoothness,
            base_amplitude_in=base_amplitude_in,
            bend_scale_in=bend_scale_in,
            flow_angle_deg=flow_angle_deg,
            flow_strength=flow_strength,
            detail=detail,
            use_mass=use_mass,
            mass_strength=mass_strength,
            samples=samples,
            smooth_passes=smooth_passes,
            add_tabs=add_tabs,
            tab_width_in=tab_width_in,
            tab_height_in=tab_height_in,
            tab_centers_in=tab_centers_in,
            delete_old=delete_old,
        )

        ui.messageBox("Done ✅")

    except:
        if ui:
            ui.messageBox("Generator failed:\n" + traceback.format_exc())
        print("Generator failed:\n", traceback.format_exc())
