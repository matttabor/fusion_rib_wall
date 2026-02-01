# ui_builder.py
# Builds the Fusion command UI (groups, descriptions, tooltips)
# + optional Presets dropdown (applies to Flow settings)

import adsk.core
import traceback

import config
import presets
from util import set_tip


def register_command(ui, handlers, generator_module):
    """
    Creates and executes the command. Keeps command definition setup in one place.
    generator_module must have execute(args) function.
    """
    cmd_id = "organicFlowRibsSurfaceFirstCmd"

    cmd_defs = ui.commandDefinitions
    existing = cmd_defs.itemById(cmd_id)
    if existing:
        existing.deleteMe()

    cmd_def = cmd_defs.addButtonDefinition(
        cmd_id,
        "Organic Flow Ribs (Surface-First)",
        "Surface-first flowing ribs with seed, flow direction, smoothing, and tabs"
    )

    on_created = CommandCreatedHandler(generator_module, handlers)
    cmd_def.commandCreated.add(on_created)
    handlers.append(on_created)

    cmd_def.execute()


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self, generator_module, handlers):
        super().__init__()
        self.generator_module = generator_module
        self.handlers = handlers

    def notify(self, args):
        ui = None
        try:
            app = adsk.core.Application.get()
            ui = app.userInterface

            cmd = args.command
            inputs = cmd.commandInputs

            # ----------------------------
            # Groups
            # ----------------------------
            g_main = inputs.addGroupCommandInput("grpMain", "Main")
            g_main.isExpanded = True
            main = g_main.children

            g_flow = inputs.addGroupCommandInput("grpFlow", "Flow Surface Controls")
            g_flow.isExpanded = True
            flow = g_flow.children

            g_quality = inputs.addGroupCommandInput("grpQuality", "Quality and Smoothing")
            g_quality.isExpanded = True
            qual = g_quality.children

            g_tabs = inputs.addGroupCommandInput("grpTabs", "Tabs")
            g_tabs.isExpanded = True
            tabs = g_tabs.children

            g_house = inputs.addGroupCommandInput("grpHouse", "Housekeeping")
            g_house.isExpanded = False
            house = g_house.children

            # ----------------------------
            # MAIN
            # ----------------------------
            d_main = config.DEFAULTS_MAIN

            rib_count = main.addIntegerSpinnerCommandInput(
                "ribCount", "Number of ribs",
                config.LIMITS["rib_count"][0],
                config.LIMITS["rib_count"][1],
                1,
                d_main["rib_count"]
            )
            set_tip(
                rib_count,
                "How many ribs to generate",
                "More ribs = smoother sculpture appearance, more parts to cut.\nCommon: 20–60."
            )

            rib_len = main.addValueInput(
                "ribLength", "Rib length", "in",
                adsk.core.ValueInput.createByString(f'{d_main["rib_length_in"]} in')
            )
            set_tip(rib_len, "Length of each rib (X direction)", "This is the long dimension you cut from plywood.")

            rib_h = main.addValueInput(
                "ribHeight", "Rib height (max)", "in",
                adsk.core.ValueInput.createByString(f'{d_main["rib_height_in"]} in')
            )
            set_tip(
                rib_h,
                "Maximum rib height (Z direction)",
                "The surface is clamped so it never exceeds this height.\nTabs may extend below baseline if enabled."
            )

            rib_t = main.addValueInput(
                "ribThickness", "Rib thickness", "in",
                adsk.core.ValueInput.createByString(f'{d_main["rib_thickness_in"]} in')
            )
            set_tip(rib_t, "Plywood thickness (extrusion distance)", "Measure your sheet if you want a perfect press-fit slot.")

            gap = main.addValueInput(
                "gapBetweenRibs", "Gap between ribs (preview)", "in",
                adsk.core.ValueInput.createByString(f'{d_main["gap_between_ribs_in"]} in')
            )
            set_tip(
                gap,
                "Spacing between ribs for the wall-preview layout",
                "Does not affect cut geometry.\nOnly spreads ribs so you can see assembled look."
            )

            layout_y = main.addBoolValueInput("layoutAlongY", "Layout along Y (stack depth)", True, "", d_main["layout_along_y"])
            set_tip(layout_y, "If ON: ribs are spaced along Y. If OFF: along X", "ON is best for stacked sculpture preview.")

            # ----------------------------
            # FLOW
            # ----------------------------
            d_flow = config.DEFAULTS_FLOW

            # Preset dropdown
            preset_dd = flow.addDropDownCommandInput(
                "presetPick",
                "Preset",
                adsk.core.DropDownStyles.TextListDropDownStyle
            )
            for name in presets.preset_names():
                preset_dd.listItems.add(name, name == presets.PRESET_LABEL_NONE)

            set_tip(
                preset_dd,
                "Quick starting points",
                "Pick a preset to auto-fill the Flow settings.\nYou can still tweak after applying."
            )

            flow.addSeparatorCommandInput("flowPresetSep")

            flow.addTextBoxCommandInput(
                "flowDescription",
                "",
                "This generator defines a <b>2D flowing surface</b> z = f(x, y), then samples it into ribs.<br>"
                "That’s what creates the calm reference look: coherent motion across ribs (not one curve shifted).",
                4,
                True
            )

            seed = flow.addIntegerSpinnerCommandInput("seed", "Seed (signed int)", -2147483648, 2147483647, 1, d_flow["seed"])
            set_tip(seed, "Deterministic seed", "Same seed + same parameters = same model.\nChange seed to explore new variations.")

            randomness = flow.addValueInput("randomness", "Randomness (0–1)", "", adsk.core.ValueInput.createByString(str(d_flow["randomness"])))
            set_tip(
                randomness,
                "Master intensity for variation",
                "Scales surface complexity.\n0.0 = very uniform flow\n1.0 = more complex flow (still smooth)."
            )

            wildness = flow.addValueInput("wildness", "Wildness (0–1)", "", adsk.core.ValueInput.createByString(str(d_flow["wildness"])))
            set_tip(
                wildness,
                "Corner sweeps and dramatic direction changes",
                "Higher values create stronger diagonal sweeping behavior.\nTry 0.2–0.6."
            )

            smoothness = flow.addValueInput("smoothness", "Smoothness (0–1)", "", adsk.core.ValueInput.createByString(str(d_flow["smoothness"])))
            set_tip(
                smoothness,
                "Bias toward calm flow vs carved terrain",
                "Higher values dampen detail and keep curvature calmer.\nLower values allow richer terrain variation."
            )

            flow.addSeparatorCommandInput("flowSep0")

            base_amp = flow.addValueInput("baseAmplitude", "Base amplitude", "in", adsk.core.ValueInput.createByString(f'{d_flow["base_amplitude_in"]} in'))
            set_tip(
                base_amp,
                "Overall vertical relief of the surface",
                "This is the primary height of the flowing surface.\nClamped by Rib height."
            )

            bend_scale = flow.addValueInput("bendScale", "Bend scale (bigger = calmer)", "in",
                                            adsk.core.ValueInput.createByString(f'{d_flow["bend_scale_in"]} in'))
            set_tip(
                bend_scale,
                "Controls the size of the primary flow features",
                "Think of this as the dune size.\nBigger than rib length yields broad, continuous curvature (reference-like)."
            )

            flow_angle = flow.addValueInput("flowAngleDeg", "Flow direction angle (deg)", "deg",
                                            adsk.core.ValueInput.createByString(f'{d_flow["flow_angle_deg"]} deg'))
            set_tip(
                flow_angle,
                "Direction the surface tends to sweep",
                "0° = along ribs, 90° = across ribs.\nTry 10–35° for corner-to-corner sweeps."
            )

            flow_strength = flow.addValueInput("flowStrength", "Flow strength (0–1)", "", adsk.core.ValueInput.createByString(str(d_flow["flow_strength"])))
            set_tip(
                flow_strength,
                "How strongly directionality influences the shape",
                "Higher values make features lean consistently in the chosen direction.\nKey control for the reference look."
            )

            detail = flow.addValueInput("detail", "Detail (0–1)", "", adsk.core.ValueInput.createByString(str(d_flow["detail"])))
            set_tip(
                detail,
                "Adds secondary terrain without jagged noise",
                "0 = very clean dunes\n1 = richer topography (still smooth).\nIncreases low-frequency components."
            )

            use_mass = flow.addBoolValueInput("useMass", "Add terrain mass (optional)", True, "", d_flow["use_mass"])
            set_tip(
                use_mass,
                "Adds a broad smooth 'mass' region",
                "Off matches the clean reference style.\nOn adds a gentle large-scale lump (still coherent)."
            )

            mass_strength = flow.addValueInput("massStrength", "Mass strength (0–1)", "", adsk.core.ValueInput.createByString(str(d_flow["mass_strength"])))
            set_tip(
                mass_strength,
                "Strength of the terrain mass",
                "Only applies when terrain mass is enabled.\nKeep small for subtlety (0.1–0.35)."
            )

            # ----------------------------
            # QUALITY
            # ----------------------------
            d_q = config.DEFAULTS_QUALITY

            qual.addTextBoxCommandInput(
                "qualityDescription",
                "",
                "Quality controls affect smoothness and runtime.<br>"
                "If you see rough shading or tiny kinks, increase samples and/or smoothing passes.",
                3,
                True
            )

            samples = qual.addIntegerSpinnerCommandInput(
                "samples",
                "Spline samples",
                config.LIMITS["samples"][0],
                config.LIMITS["samples"][1],
                10,
                d_q["samples"]
            )
            set_tip(samples, "How many points are used to fit the spline", "Higher = smoother, slower.\nTypical: 320–520.")

            smooth_passes = qual.addIntegerSpinnerCommandInput(
                "smoothPasses",
                "Smoothing passes",
                config.LIMITS["smooth_passes"][0],
                config.LIMITS["smooth_passes"][1],
                1,
                d_q["smooth_passes"]
            )
            set_tip(
                smooth_passes,
                "Post-smoothing on Z values",
                "Runs a small moving-average filter across the profile.\nTry 2–4 if your curve looks faceted."
            )

            # ----------------------------
            # TABS
            # ----------------------------
            d_tabs = config.DEFAULTS_TABS

            tabs.addTextBoxCommandInput(
                "tabsDescription",
                "",
                "Tabs are how each rib connects to the wall panel.<br>"
                "They are cut as part of the rib profile and slot into matching pockets in a backer panel for alignment.",
                3,
                True
            )
            tabs.addSeparatorCommandInput("tabsSepA")

            add_tabs = tabs.addBoolValueInput("addTabs", "Add tabs (2D tenons)", True, "", d_tabs["add_tabs"])
            set_tip(
                add_tabs,
                "Adds rectangular tabs below baseline",
                "Tabs extend into negative Z and extrude with the rib.\nYour wall panel should have matching slots."
            )

            tab_w = tabs.addValueInput("tabWidth", "Tab width", "in", adsk.core.ValueInput.createByString(f'{d_tabs["tab_width_in"]} in'))
            set_tip(tab_w, "Width of each tab along rib length", "Typical: 3–6 inches.")

            tab_h = tabs.addValueInput("tabHeight", "Tab height", "in", adsk.core.ValueInput.createByString(f'{d_tabs["tab_height_in"]} in'))
            set_tip(tab_h, "How far tabs extend below baseline", "This is the tenon depth.\nMatch your panel pocket depth to this.")

            centers_default = ",".join([str(v) for v in d_tabs["tab_centers_in"]])
            tab_centers = tabs.addStringValueInput("tabCenters", "Tab centers (in, comma-separated)", centers_default)
            set_tip(tab_centers, "Centers of tabs along the length", "Example: 16,32 makes two tabs.\nAdd more like 10,24,38")

            tabs.addSeparatorCommandInput("tabsSepB")

            # ----------------------------
            # HOUSEKEEPING
            # ----------------------------
            delete_old = house.addBoolValueInput("deleteOld", "Delete previous OrganicFlowRibs_* containers", True, "", True)
            set_tip(delete_old, "Auto-clean previous runs", "Deletes root-level occurrences whose component name starts with OrganicFlowRibs_.")

            # Wire Execute/Destroy
            on_execute = CommandExecuteHandler(self.generator_module)
            cmd.execute.add(on_execute)
            self.handlers.append(on_execute)

            # Preset apply
            on_changed = InputChangedHandler()
            cmd.inputChanged.add(on_changed)
            self.handlers.append(on_changed)

            on_destroy = CommandDestroyHandler()
            cmd.destroy.add(on_destroy)
            self.handlers.append(on_destroy)

        except:
            if ui:
                ui.messageBox("UI build failed:\n" + traceback.format_exc())


class CommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self, generator_module):
        super().__init__()
        self.generator_module = generator_module

    def notify(self, args):
        self.generator_module.execute(args)


class InputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            changed = args.input
            if not changed:
                return

            if changed.id == "presetPick":
                presets.apply_preset_to_inputs(args.inputs, changed.selectedItem.name)
        except:
            # Avoid modal errors while dragging sliders/inputs
            pass


class CommandDestroyHandler(adsk.core.CommandEventHandler):
    def notify(self, args):
        try:
            adsk.terminate()
        except:
            pass
