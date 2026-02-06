# util.py
# Small shared helpers for Organic Flow Ribs

import adsk.core
import adsk.fusion
import math


# ----------------------------
# UI helpers
# ----------------------------

def set_tip(inp, tooltip, description=None):
    """Safely set tooltip + optional tooltipDescription."""
    try:
        inp.tooltip = tooltip
        if description is not None:
            inp.tooltipDescription = description
    except:
        pass


# ----------------------------
# Math helpers
# ----------------------------

def clamp(val, lo, hi):
    return max(lo, min(hi, val))


def clamp01(val):
    return clamp(val, 0.0, 1.0)


# ----------------------------
# Units
# ----------------------------

def inches_from_value_input(value_input):
    """
    Fusion ValueInput .value is in cm internally.
    Convert to inches.
    """
    return value_input.value / 2.54


def cm(val_in_inches):
    return val_in_inches * 2.54


def deg_to_rad(deg):
    return deg * math.pi / 180.0


# ----------------------------
# Parsing helpers
# ----------------------------

def parse_float_list(csv_text):
    """
    Parse a comma-separated list of floats.
    Example: "16, 32, 48" -> [16.0, 32.0, 48.0]
    """
    if not csv_text:
        return []

    out = []
    for part in csv_text.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(float(part))
    return out


# ----------------------------
# Geometry helpers
# ----------------------------

def smooth_series(values, passes=2):
    """
    Light smoothing to remove tiny kinks without killing large-scale shape.
    Uses a simple 1D moving-average filter.
    """
    if passes <= 0:
        return values

    out = list(values)
    for _ in range(passes):
        if len(out) < 3:
            return out
        out = (
            [out[0]] +
            [
                0.25 * out[i - 1] + 0.5 * out[i] + 0.25 * out[i + 1]
                for i in range(1, len(out) - 1)
            ] +
            [out[-1]]
        )
    return out


# ----------------------------
# Fusion cleanup helpers
# ----------------------------

def delete_containers_with_prefix(root_component, prefix):
    """
    Deletes root-level occurrences whose component name starts with prefix.
    Useful for cleaning previous runs.
    """
    occs = root_component.occurrences
    to_delete = []

    for occ in occs:
        try:
            comp = occ.component
            if comp and comp.name.startswith(prefix):
                to_delete.append(occ)
        except:
            pass

    for occ in to_delete:
        try:
            occ.deleteMe()
        except:
            pass


# ----------------------------
# Tab helpers
# ----------------------------

def build_tab_spans(tab_centers_in, tab_width_in, rib_length_in):
    """
    Given tab centers and width, return spans [(x0, x1), ...]
    sorted right-to-left for easy baseline construction.
    """
    spans = []
    for c in tab_centers_in:
        x0 = max(0.0, c - tab_width_in / 2.0)
        x1 = min(rib_length_in, c + tab_width_in / 2.0)
        if x1 > x0:
            spans.append((x0, x1))

    spans.sort(key=lambda t: t[0], reverse=True)
    return spans

def _delete_old_runs(root, prefix: str):
    to_delete = []
    for i in range(root.occurrences.count):
        occ = root.occurrences.item(i)
        if occ and occ.component and occ.component.name.startswith(prefix):
            to_delete.append(occ)
    for occ in reversed(to_delete):
        try:
            occ.deleteMe()
        except:
            pass