# presets.py
# Optional preset dropdown + apply logic for Organic Flow Ribs

import config


PRESET_LABEL_NONE = "Custom (no change)"


def preset_names():
    return [PRESET_LABEL_NONE] + list(config.PRESETS.keys())


def apply_preset_to_inputs(inputs, preset_name: str):
    """
    Applies preset values into existing CommandInputs by ID.
    Safe to call from an inputChanged handler.
    """
    if preset_name == PRESET_LABEL_NONE:
        return

    preset = config.PRESETS.get(preset_name)
    if not preset:
        return

    # Helpers: set unitless numeric, set inches ValueInputs, set bools
    def set_unitless(input_id, val):
        try:
            inputs.itemById(input_id).value = float(val)
        except:
            pass

    def set_inches(input_id, inches_val):
        try:
            # ValueInput expects cm in .value
            inputs.itemById(input_id).value = float(inches_val) * 2.54
        except:
            pass

    def set_bool(input_id, val):
        try:
            inputs.itemById(input_id).value = bool(val)
        except:
            pass

    # Map known preset keys to your input IDs
    # Unitless
    if "randomness" in preset: set_unitless("randomness", preset["randomness"])
    if "wildness" in preset: set_unitless("wildness", preset["wildness"])
    if "smoothness" in preset: set_unitless("smoothness", preset["smoothness"])
    if "detail" in preset: set_unitless("detail", preset["detail"])
    if "flow_strength" in preset: set_unitless("flowStrength", preset["flow_strength"])
    if "mass_strength" in preset: set_unitless("massStrength", preset["mass_strength"])

    # Inches
    if "bend_scale_in" in preset: set_inches("bendScale", preset["bend_scale_in"])

    # Bool
    if "use_mass" in preset: set_bool("useMass", preset["use_mass"])
