# src/backer_panel/backer.py
#
# Backer panel generator for OrganicFlowRibs
# -----------------------------------------
# Creates a backer plate (own component) and cuts tab pockets into it.
#
# Key behaviors:
# - Backer length is based on the tab-span + margins, clamped to rib_length_in
# - Backer stack span covers the full rib stack (rib_count * pitch)
# - Backer is placed BEHIND the ribs by shifting -Z so the front face sits at Z=0
# - Pocket cuts are reliable:
#     * direction flipped
#     * participant body explicitly set
#
# IMPORTANT NOTE ABOUT COORDS (legacy-compatible):
# - Tabs are created in rib profiles by dropping the "bottom" of the profile to -tab_height_in.
#   That means tab volume lives in negative Z.
# - This backer is therefore positioned in [-backer_thickness .. 0] on Z so it sits where tabs exist.

import adsk.core
import adsk.fusion
from util import cm


def _compose_transform(occ: adsk.fusion.Occurrence, extra: adsk.core.Matrix3D) -> None:
    """
    Safely compose transforms: occ.transform = occ.transform * extra
    """
    current = occ.transform.copy()
    current.transformBy(extra)
    occ.transform = current


def build_backer_panel(
    container_comp: adsk.fusion.Component,
    *,
    rib_count: int,
    rib_length_in: float,
    rib_thickness_in: float,
    gap_between_ribs_in: float,
    layout_along_y: bool,
    add_tabs: bool,
    tab_width_in: float,
    tab_height_in: float,
    tab_centers_in,
    backer_thickness_in: float,
    backer_tab_clearance_in: float,
    backer_margin_in: float,
):
    app = adsk.core.Application.get()
    ui = app.userInterface

    if not add_tabs or not tab_centers_in:
        ui.messageBox("Backer panel requested, but tabs are disabled or no tab centers were provided.")
        return None

    rib_count = max(1, int(rib_count))
    rib_length_in = max(0.01, float(rib_length_in))
    rib_thickness_in = max(0.01, float(rib_thickness_in))
    gap_between_ribs_in = max(0.0, float(gap_between_ribs_in))
    backer_thickness_in = max(0.01, float(backer_thickness_in))
    backer_tab_clearance_in = max(0.0, float(backer_tab_clearance_in))
    backer_margin_in = max(0.0, float(backer_margin_in))

    pitch_in = rib_thickness_in + gap_between_ribs_in
    stack_span_in = (rib_count - 1) * pitch_in + rib_thickness_in

    # Build tab spans along rib length
    spans = []
    for c in tab_centers_in:
        c = float(c)
        x0 = max(0.0, c - tab_width_in / 2.0)
        x1 = min(rib_length_in, c + tab_width_in / 2.0)
        if x1 > x0:
            spans.append((x0, x1))

    if not spans:
        ui.messageBox("Backer panel: no valid tab spans were computed.")
        return None

    min_x = min(s[0] for s in spans)
    max_x = max(s[1] for s in spans)

    # Backer length is tab-span +/- margin, clamped to [0..rib_length_in]
    backer_x0 = max(0.0, min_x - backer_margin_in)
    backer_x1 = min(rib_length_in, max_x + backer_margin_in)
    if backer_x1 <= backer_x0:
        ui.messageBox("Backer panel: computed backer length is invalid.")
        return None

    # Create component for backer
    occ = container_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = "BackerPanel"

    # --- Base plate ---
    # We draw the plate in the component's XY plane:
    #   X = rib length segment [backer_x0..backer_x1]
    #   Y = stack span [0..stack_span_in]
    sk = comp.sketches.add(comp.xYConstructionPlane)
    lines = sk.sketchCurves.sketchLines

    p0 = adsk.core.Point3D.create(cm(backer_x0), 0, 0)
    p1 = adsk.core.Point3D.create(cm(backer_x1), 0, 0)
    p2 = adsk.core.Point3D.create(cm(backer_x1), cm(stack_span_in), 0)
    p3 = adsk.core.Point3D.create(cm(backer_x0), cm(stack_span_in), 0)

    lines.addByTwoPoints(p0, p1)
    lines.addByTwoPoints(p1, p2)
    lines.addByTwoPoints(p2, p3)
    lines.addByTwoPoints(p3, p0)

    if sk.profiles.count == 0:
        ui.messageBox("Backer panel: failed to create base profile.")
        return None

    prof = sk.profiles.item(0)

    ext = comp.features.extrudeFeatures
    ei = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ei.setDistanceExtent(False, adsk.core.ValueInput.createByString(f"{backer_thickness_in} in"))
    base_feat = ext.add(ei)
    body = base_feat.bodies.item(0)

    # --- Placement / alignment ---
    # We want the backer plate's FRONT face to sit at Z=0 (rib back plane),
    # so the plate spans [-thickness .. 0].
    if not layout_along_y:
        rz = adsk.core.Matrix3D.create()
        rz.setToRotation(-3.141592653589793 / 2.0,
                        adsk.core.Vector3D.create(0, 0, 1),
                        adsk.core.Point3D.create(0, 0, 0))
        _compose_transform(occ, rz)

    # Always apply the -Z placement LAST so it stays "behind" after any rotation.
    tz = adsk.core.Matrix3D.create()
    tz.translation = adsk.core.Vector3D.create(0, 0, cm(-backer_thickness_in))
    _compose_transform(occ, tz)

    # --- Pocket sketch on the face at max Z (this is the "front" face at Z=0 after placement) ---
    front_face = max(body.faces, key=lambda f: f.boundingBox.maxPoint.z)

    sk2 = comp.sketches.add(front_face)
    sl = sk2.sketchCurves.sketchLines

    clear = backer_tab_clearance_in

    # Create pockets for each rib at its stack position
    for i in range(rib_count):
        stack0 = i * pitch_in
        stack1 = stack0 + rib_thickness_in

        for (t0, t1) in spans:
            # Expand pocket along length slightly
            a0 = max(0.0, t0 - clear)
            a1 = min(rib_length_in, t1 + clear)

            # Optionally shrink/expand along stack a hair; keep sane if clearance is big
            b0 = stack0 + clear
            b1 = stack1 - clear
            if b1 <= b0:
                b0 = stack0
                b1 = stack1

            q0 = adsk.core.Point3D.create(cm(a0), cm(b0), 0)
            q1 = adsk.core.Point3D.create(cm(a1), cm(b0), 0)
            q2 = adsk.core.Point3D.create(cm(a1), cm(b1), 0)
            q3 = adsk.core.Point3D.create(cm(a0), cm(b1), 0)

            sl.addByTwoPoints(q0, q1)
            sl.addByTwoPoints(q1, q2)
            sl.addByTwoPoints(q2, q3)
            sl.addByTwoPoints(q3, q0)

    if sk2.profiles.count == 0:
        ui.messageBox("Backer panel: pocket profiles failed (no profiles created).")
        return occ

    # Collect all pocket profiles
    profs = adsk.core.ObjectCollection.create()
    for k in range(sk2.profiles.count):
        profs.add(sk2.profiles.item(k))

    # Cut pockets through the backer thickness
    ci = ext.createInput(profs, adsk.fusion.FeatureOperations.CutFeatureOperation)

    # Through all is the most robust extent for cuts.
    ci.setAllExtent(adsk.fusion.ExtentDirections.PositiveExtentDirection)

    # If the cut goes the wrong way, flip it. (This is the usual case when sketching on the "front" face.)
    ci.isDirectionFlipped = True

    ext.add(ci)

    return occ
