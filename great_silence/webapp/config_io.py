"""Configuration file I/O for the webapp."""

from nicegui import ui, events
from pathlib import Path
import yaml
import os

from .state import app_state
from great_silence.config.parameters import SimulationConfig


def create_load_config_dialog(on_load_callback=None):
    """Create a dialog for loading configuration from YAML file."""

    dialog = ui.dialog()

    with dialog, ui.card().classes("w-96"):
        ui.label("Load Configuration").classes("text-lg font-semibold text-gray-300 mb-4")

        upload = ui.upload(
            label="Select YAML file",
            auto_upload=True,
            on_upload=lambda e: _handle_upload(e, dialog, on_load_callback),
        ).props('accept=".yaml,.yml"').classes("w-full")

        ui.label("Or enter path:").classes("text-gray-400 text-sm mt-4")
        path_input = ui.input(placeholder="/path/to/config.yaml").classes("w-full").props(
            "dense outlined dark"
        )

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Load",
                on_click=lambda: _load_from_path(path_input.value, dialog, on_load_callback),
            ).classes("bg-green-700")

    return dialog


def _handle_upload(e: events.UploadEventArguments, dialog, on_load_callback):
    """Handle uploaded YAML file."""
    try:
        content = e.content.read().decode("utf-8")
        data = yaml.safe_load(content)

        _apply_config_data(data)

        dialog.close()
        ui.notify(f"Loaded configuration from {e.name}", type="positive")

        if on_load_callback:
            on_load_callback()

    except Exception as ex:
        ui.notify(f"Error loading config: {ex}", type="negative")


def _load_from_path(path: str, dialog, on_load_callback):
    """Load configuration from a file path."""
    if not path:
        ui.notify("Please enter a path", type="warning")
        return

    try:
        path = Path(path).expanduser()
        if not path.exists():
            ui.notify(f"File not found: {path}", type="negative")
            return

        config = SimulationConfig.from_yaml(str(path))
        app_state.config = config

        dialog.close()
        ui.notify(f"Loaded configuration from {path.name}", type="positive")

        if on_load_callback:
            on_load_callback()

    except Exception as ex:
        ui.notify(f"Error loading config: {ex}", type="negative")


def _apply_config_data(data: dict):
    """Apply configuration data to app state."""
    if "galaxy" in data:
        for key, value in data["galaxy"].items():
            if hasattr(app_state.config.galaxy, key):
                setattr(app_state.config.galaxy, key, value)

    if "astrophysics" in data:
        for key, value in data["astrophysics"].items():
            if hasattr(app_state.config.astrophysics, key):
                setattr(app_state.config.astrophysics, key, value)

    if "civilization" in data:
        for key, value in data["civilization"].items():
            if hasattr(app_state.config.civilization, key):
                setattr(app_state.config.civilization, key, value)

    if "simulation" in data:
        for key, value in data["simulation"].items():
            if hasattr(app_state.config.simulation, key):
                setattr(app_state.config.simulation, key, value)


def create_save_config_dialog():
    """Create a dialog for saving configuration to YAML file."""

    dialog = ui.dialog()

    with dialog, ui.card().classes("w-96"):
        ui.label("Save Configuration").classes("text-lg font-semibold text-gray-300 mb-4")

        ui.label("Enter filename:").classes("text-gray-400 text-sm")
        filename_input = ui.input(value="my_config.yaml", placeholder="config.yaml").classes(
            "w-full"
        ).props("dense outlined dark")

        ui.label("Save location:").classes("text-gray-400 text-sm mt-4")
        dir_input = ui.input(value="output", placeholder="directory").classes("w-full").props(
            "dense outlined dark"
        )

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Save",
                on_click=lambda: _save_config(filename_input.value, dir_input.value, dialog),
            ).classes("bg-green-700")

    return dialog


def _save_config(filename: str, directory: str, dialog):
    """Save configuration to file."""
    if not filename:
        ui.notify("Please enter a filename", type="warning")
        return

    try:
        if not filename.endswith((".yaml", ".yml")):
            filename += ".yaml"

        output_dir = Path(directory).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        app_state.config.to_yaml(str(output_path))

        dialog.close()
        ui.notify(f"Saved to {output_path}", type="positive")

    except Exception as ex:
        ui.notify(f"Error saving config: {ex}", type="negative")


def create_save_preset_dialog(on_save_callback=None):
    """Create a dialog for saving current config as a custom preset."""

    dialog = ui.dialog()

    with dialog, ui.card().classes("w-96"):
        ui.label("Save as Custom Preset").classes("text-lg font-semibold text-gray-300 mb-4")

        ui.label("Preset Name:").classes("text-gray-400 text-sm")
        name_input = ui.input(placeholder="My Scenario").classes("w-full").props(
            "dense outlined dark"
        )

        ui.label("Description (optional):").classes("text-gray-400 text-sm mt-4")
        desc_input = (
            ui.textarea(placeholder="Brief description of this scenario...")
            .classes("w-full")
            .props("dense outlined dark rows=3")
        )

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button(
                "Save Preset",
                on_click=lambda: _save_preset(name_input.value, desc_input.value, dialog, on_save_callback),
            ).classes("bg-purple-700")

    return dialog


def _save_preset(name: str, description: str, dialog, callback):
    """Save current configuration as a custom preset."""
    if not name:
        ui.notify("Please enter a preset name", type="warning")
        return

    try:
        presets_dir = Path.home() / ".great_silence" / "presets"
        presets_dir.mkdir(parents=True, exist_ok=True)

        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in name)
        preset_path = presets_dir / f"{safe_name}.yaml"

        config_data = app_state.config.to_dict()
        config_data["_preset_meta"] = {
            "name": name,
            "description": description,
        }

        with open(preset_path, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

        dialog.close()
        ui.notify(f"Saved preset '{name}'", type="positive")

        if callback:
            callback()

    except Exception as ex:
        ui.notify(f"Error saving preset: {ex}", type="negative")


def get_custom_presets() -> list:
    """Get list of custom presets from user directory."""
    presets_dir = Path.home() / ".great_silence" / "presets"
    if not presets_dir.exists():
        return []

    presets = []
    for preset_file in presets_dir.glob("*.yaml"):
        try:
            with open(preset_file) as f:
                data = yaml.safe_load(f)
            meta = data.get("_preset_meta", {})
            presets.append({
                "path": str(preset_file),
                "name": meta.get("name", preset_file.stem),
                "description": meta.get("description", ""),
            })
        except Exception:
            continue

    return presets
