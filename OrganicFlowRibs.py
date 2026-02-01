# OrganicFlowRibs.py
# Entry point for Fusion 360 Script
#
# Folder layout (all files in the same folder):
#   OrganicFlowRibs.py
#   config.py
#   util.py
#   ui_builder.py
#   generator.py
#   geometry.py

import adsk.core
import traceback
import importlib

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

        adsk.autoTerminate(False)

    except:
        if ui:
            ui.messageBox("Failed:\n" + traceback.format_exc())


def stop(context):
    # Optional: Fusion calls stop() for Add-Ins; scripts typically don't need it.
    # Leaving it here doesn't hurt and can help if you later convert to an Add-In.
    try:
        adsk.terminate()
    except:
        pass
