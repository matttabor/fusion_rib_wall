# config.py
# Centralized defaults, limits, and presets for Organic Flow Ribs

# ----------------------------
# Metadata / Naming
# ----------------------------

SCRIPT_PREFIX = "OrganicFlowRibs_"

# ----------------------------
# Main geometry defaults
# ----------------------------

DEFAULTS_MAIN = {
    "rib_count": 30,
    "rib_length_in": 48.0,
    "rib_height_in": 4.0,
    "rib_thickness_in": 0.75,
    "gap_between_ribs_in": 1.0,
    "layout_along_y": True,
}

# ----------------------------
# Flow / surface defaults
# ----------------------------

DEFAULTS_FLOW = {
    "seed": 12345,

    # Big style knobs
    "randomness": 0.35,   # 0..1
    "wildness": 0.25,     # 0..1
    "smoothness": 0.80,   # 0..1

    # Vertical relief
    "base_amplitude_in": 1.10,

    # Primary bend size (bigger = calmer, reference-like)
    "bend_scale_in": 72.0,

    # Directional flow
    # Degrees in UI, radians in math
    "flow_angle_deg": 18.0,
    "flow_strength": 0.55,

    # Secondary terrain richness (still smooth)
    "detail": 0.35,

    # Optional terrain mass
    "use_mass": False,
    "mass_strength": 0.25,
}

# ----------------------------
# Quality / smoothing defaults
# ----------------------------

DEFAULTS_QUALITY = {
    "samples": 420,
    "smooth_passes": 2,
}

# ----------------------------
# Tabs (tenons) defaults
# ----------------------------

DEFAULTS_TABS = {
    "add_tabs": True,
    "tab_width_in": 4.0,
    "tab_height_in": 0.675,
    "tab_centers_in": [16.0, 32.0],
}

# ----------------------------
# Validation limits
# ----------------------------

LIMITS = {
    "rib_count": (1, 600),
    "rib_length_in": (1.0, 144.0),
    "rib_height_in": (0.25, 12.0),
    "rib_thickness_in": (0.25, 2.0),
    "gap_between_ribs_in": (0.0, 6.0),

    "randomness": (0.0, 1.0),
    "wildness": (0.0, 1.0),
    "smoothness": (0.0, 1.0),

    "base_amplitude_in": (0.0, 12.0),
    "bend_scale_in": (6.0, 240.0),
    "flow_angle_deg": (-180.0, 180.0),
    "flow_strength": (0.0, 1.0),
    "detail": (0.0, 1.0),

    "mass_strength": (0.0, 1.0),

    "samples": (80, 1200),
    "smooth_passes": (0, 10),

    "tab_width_in": (0.5, 12.0),
    "tab_height_in": (0.1, 3.0),
}

# ----------------------------
# Presets (optional, future UI use)
# ----------------------------

PRESETS = {
    "Clean Dunes": {
        "randomness": 0.25,
        "wildness": 0.15,
        "smoothness": 0.90,
        "detail": 0.20,
        "flow_strength": 0.45,
        "bend_scale_in": 90.0,
        "use_mass": False,
    },
    "Gallery Flow": {
        "randomness": 0.35,
        "wildness": 0.30,
        "smoothness": 0.80,
        "detail": 0.35,
        "flow_strength": 0.55,
        "bend_scale_in": 72.0,
        "use_mass": False,
    },
    "Carved Terrain": {
        "randomness": 0.55,
        "wildness": 0.45,
        "smoothness": 0.60,
        "detail": 0.65,
        "flow_strength": 0.65,
        "bend_scale_in": 48.0,
        "use_mass": True,
        "mass_strength": 0.30,
    },
}
