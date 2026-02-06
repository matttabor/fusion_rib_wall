# wall.py
#
# Simple wall reference component for visualization.

import adsk.core
import adsk.fusion
from util import cm


def build_wall(
    container_comp: adsk.fusion.Component,
    *,
    wall_width_in: float,
    wall_height_in: float,
    wall_thickness_in: float,
    mount_height_in: float,
    wall_offset_in: float,
):
    occ = container_comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = "Wall"

    sk = comp.sketches.add(comp.xYConstructionPlane)
    ln = sk.sketchCurves.sketchLines

    p0 = adsk.core.Point3D.create(0, 0, 0)
    p1 = adsk.core.Point3D.create(cm(wall_width_in), 0, 0)
    p2 = adsk.core.Point3D.create(cm(wall_width_in), cm(wall_height_in), 0)
    p3 = adsk.core.Point3D.create(0, cm(wall_height_in), 0)

    ln.addByTwoPoints(p0, p1)
    ln.addByTwoPoints(p1, p2)
    ln.addByTwoPoints(p2, p3)
    ln.addByTwoPoints(p3, p0)

    prof = sk.profiles.item(0)
    ext = comp.features.extrudeFeatures
    ei = ext.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    ei.setDistanceExtent(False, adsk.core.ValueInput.createByString(f"{wall_thickness_in} in"))
    ext.add(ei)

    m = adsk.core.Matrix3D.create()
    m.translation = adsk.core.Vector3D.create(
        0,
        cm(mount_height_in),
        cm(wall_offset_in),
    )
    occ.transform = m

    return occ
