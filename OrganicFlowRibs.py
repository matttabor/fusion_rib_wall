# OrganicFlowRibs.py
# Entry point for Fusion 360 Script
import adsk.core
import traceback
import os
import sys
import importlib

# CRITICAL: add this script's folder to Python path otherwise Fusion can't
# find the other modules when they are imported
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(THIS_DIR, "src")
if THIS_DIR not in sys.path:
    sys.path.insert(0, THIS_DIR)

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import ui_builder
import generator

_handlers = []


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface

        # DEV: reload modules so edits take effect without restarting Fusion
        importlib.reload(ui_builder)
        importlib.reload(generator)

        ui_builder.register_command(ui, _handlers, generator)

        # Keep script alive so command events (execute/destroy) can fire reliably
        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox("Failed:\n" + traceback.format_exc())


def stop(context):
    # Optional: provides a clean shutdown path
    try:
        adsk.terminate()
    except:
        pass
