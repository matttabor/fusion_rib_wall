# OrganicFlowRibs  
### Parametric Wall Sculpture Generator for Autodesk Fusion 360

OrganicFlowRibs is a **Fusion 360 Python script** that procedurally generates a wall-mounted rib sculpture from a **single coherent flowing surface**. Each rib is produced as its own solid component, designed to be CNC-cut from sheet goods (e.g. 3/4" plywood) and assembled into a sculptural wall installation.

The core design goal is to create **calm, architectural, gallery-style flow** — not a stack of shifted curves. All ribs are slices through the same underlying surface: z = f(x, y)

This ensures continuity, smooth transitions, and a composed look across the entire sculpture.

---

### Sample
<video playsinline muted loop controls height="540" width="540">
  <source src="./samples/sample-wall.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>

## Table of Contents

- [Key Features](#key-features)
- [Conceptual Overview](#conceptual-overview)
- [How It Works](#how-it-works)
- [Installation & Running](#installation--running)
- [UI Parameters Explained](#ui-parameters-explained)
- [Tabs & Wall Mounting](#tabs--wall-mounting)
- [Performance & Quality](#performance--quality)
- [Known Limitations](#known-limitations)
- [Design Philosophy](#design-philosophy)
- [Future Enhancements](#future-enhancements)

---

## Key Features

- **Surface-first generation**
  - One continuous heightfield drives all ribs
  - Eliminates per-rib phase artifacts

- **Deterministic randomness**
  - Signed integer seed
  - Same seed + same inputs = identical result
  - Easy exploration of variations

- **CNC-friendly output**
  - Each rib is a closed 2D profile extruded to thickness
  - Ideal for cutting from 4'×8' plywood sheets

- **Wall mounting tabs**
  - Optional rectangular tabs (tenons)
  - Designed to slot into a backer/wall panel
  - Fully configurable placement and size

- **Preview layout**
  - Ribs spaced in 3D for visualizing assembly
  - Preview spacing does *not* affect cut geometry

- **Quality vs speed controls**
  - Adjustable sampling density
  - Post-smoothing passes for clean curvature


---

## Conceptual Overview

### Why “Surface-First” Matters

Many rib sculptures are built by:

- designing a single curve
- duplicating and shifting it

That approach introduces visible repetition and discontinuities.

**OrganicFlowRibs uses the opposite approach:**

1. Define a smooth 2D surface across the entire sculpture
2. Sample that surface consistently across ribs
3. Build ribs as slices of the same surface

The result is:

- calm, continuous flow
- smooth transitions between ribs
- no abrupt starts, stops, or phase jumps

---

## How It Works

### 1. Surface Definition

A heightfield is defined as a function of position:

- **x** — along the rib length  
- **y** — across sculpture depth (rib index × spacing)  
- **z** — surface height  

The surface combines:

- A dominant directional sine component
- Secondary broad modulation
- Low-frequency terrain components
- Optional Gaussian “mass”
- Smooth end envelopes to avoid sharp curvature cutoffs

All randomness is **seeded**, making output fully deterministic.

---

### 2. Rib Construction

For each rib:

1. Sample `z = f(x, y)` at evenly spaced x-values
2. Apply smoothing passes to height samples
3. Build a closed sketch:
   - Top edge: fitted spline
   - Bottom edge: baseline with optional tabs
4. Extrude the sketch to material thickness
5. Position the rib in preview layout space

Each rib is created as its **own component** inside a container component.

---

## Installation & Running

### Linked Folder Setup (Recommended)

This script is designed to run from an arbitrary folder on disk.

1. Open Fusion 360
2. Utilities → Scripts and Add-Ins
3. Scripts tab → **Add** → **Link Folder**
4. Link the folder containing `OrganicFlowRibs.py`

> Fusion does **not** automatically add linked folders to Python’s import path.  
> The entry script explicitly injects its directory into `sys.path`.

---

### Running the Script

1. Open or create a Fusion **Design**
2. Run **Organic Flow Ribs (Surface-First)** from the Scripts panel
3. Adjust parameters
4. Click **OK**
5. A progress dialog appears while geometry is generated

Generated geometry appears as:

`OrganicFlowRibs_<ribCount>x_seed<seed>`


---

## UI Parameters Explained

### Main

- **Number of ribs**  
  Total ribs (and physical parts)

- **Rib length**  
  Long dimension of each rib

- **Rib height (max)**  
  Maximum profile height

- **Rib thickness**  
  Material thickness

- **Gap between ribs (preview)**  
  Visual spacing only

- **Layout along Y**  
  Controls preview orientation

---

### Flow Surface Controls

- **Seed** — deterministic variation
- **Randomness** — overall variation intensity
- **Wildness** — diagonal sweep strength
- **Smoothness** — curvature calmness
- **Base amplitude** — surface height
- **Bend scale** — size of major flow features
- **Flow direction angle** — dominant sweep direction
- **Flow strength** — direction influence
- **Detail** — secondary terrain richness
- **Terrain mass** — optional large-scale form

---

### Quality & Smoothing

- **Spline samples** — profile resolution
- **Smoothing passes** — post-process smoothing

Lower samples + more smoothing is often faster *and* smoother.

---

## Tabs & Wall Mounting

Tabs are rectangular tenons integrated into the rib profile.

- **Add tabs**
- **Tab width**
- **Tab height**
- **Tab centers (comma-separated inches)**

Designed to slot into a matching wall or backer panel for alignment and support.

---

## Performance & Quality

### Fast Iteration

- 8–14 ribs  
- 220–280 samples  
- 2–3 smoothing passes  

### Final Build

- 24–36 ribs  
- 360–520 samples  
- 3–4 smoothing passes  

---

## Known Limitations

- No DXF export yet
- No automatic sheet nesting
- Wall/backer panel not generated
- No live slider preview

---

## Design Philosophy

This project prioritizes:

- Coherent surfaces over noise
- Determinism over chaos
- Broad curvature over micro-detail
- CNC practicality over abstraction

The goal is **composed architectural flow**, not random waves.

---

## Future Enhancements

- Wall/backer panel generator
- DXF export per rib
- Automatic nesting
- Quality presets (Fast / Final)
- Preview-only mode
---
