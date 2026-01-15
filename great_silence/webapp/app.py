"""Main NiceGUI web application for Great Silence simulations."""

from nicegui import ui, app
from pathlib import Path

from .state import app_state
from .components import PresetSelector, BasicSettings, SimulationRunner, ConfigPanels, ResultsDashboard, ParameterPlots
from .config_io import create_load_config_dialog, create_save_config_dialog, create_save_preset_dialog


def apply_dark_theme():
    """Apply dark space theme to the application."""
    ui.add_head_html("""
    <style>
        :root {
            --q-dark: #1a1a2e;
            --q-dark-page: #16213e;
        }
        body {
            background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #24243e 100%);
            min-height: 100vh;
        }
        .q-card {
            background: rgba(30, 30, 50, 0.8) !important;
            border: 1px solid rgba(100, 100, 150, 0.2);
            backdrop-filter: blur(10px);
        }
        .q-expansion-item {
            background: rgba(30, 30, 50, 0.6) !important;
        }
        .q-slider__track {
            background: rgba(100, 100, 150, 0.3) !important;
        }
        .q-slider__selection {
            background: #06b6d4 !important;
        }
        .q-linear-progress__track {
            background: rgba(100, 100, 150, 0.3) !important;
        }
        .q-linear-progress__model {
            background: linear-gradient(90deg, #06b6d4, #22d3ee) !important;
        }
        .nicegui-content {
            padding: 0 !important;
        }
        ::-webkit-scrollbar {
            width: 8px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(30, 30, 50, 0.5);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(100, 100, 150, 0.5);
            border-radius: 4px;
        }
        .star-field {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: -1;
        }
        @keyframes twinkle {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 1; }
        }
    </style>
    """)


basic_settings_component = None
parameter_plots_component = None


def on_preset_select(preset_name: str) -> None:
    """Handle preset selection."""
    app_state.apply_preset(preset_name)
    ui.notify(f"Applied '{preset_name}' preset", type="positive", position="top")
    refresh_plots()


def refresh_plots() -> None:
    """Refresh parameter visualization plots."""
    global parameter_plots_component
    if parameter_plots_component:
        parameter_plots_component.refresh()


def refresh_ui_from_state():
    """Refresh UI components after loading config."""
    app_state._notify_update()
    ui.notify("Configuration loaded - UI updated", type="info")


@ui.page("/")
def main_page():
    """Main application page."""
    global basic_settings_component

    apply_dark_theme()
    ui.dark_mode().enable()

    load_dialog = create_load_config_dialog(on_load_callback=refresh_ui_from_state)
    save_dialog = create_save_config_dialog()
    preset_dialog = create_save_preset_dialog()

    with ui.header().classes(
        "bg-gray-900/80 backdrop-blur-sm border-b border-gray-700/50 items-center"
    ):
        with ui.row().classes("w-full max-w-6xl mx-auto items-center px-4"):
            ui.label("🌌").classes("text-3xl")
            with ui.column().classes("gap-0"):
                ui.label("GREAT SILENCE").classes(
                    "text-xl font-bold tracking-wider text-transparent bg-clip-text "
                    "bg-gradient-to-r from-cyan-400 to-purple-500"
                )
                ui.label("Galactic Civilization Simulator").classes("text-gray-500 text-xs")

            ui.space()

            with ui.button_group().props("flat"):
                ui.button(icon="folder_open", on_click=load_dialog.open).props("flat").tooltip(
                    "Load Configuration"
                ).classes("text-gray-400 hover:text-cyan-400")
                ui.button(icon="save", on_click=save_dialog.open).props("flat").tooltip(
                    "Save Configuration"
                ).classes("text-gray-400 hover:text-cyan-400")
                ui.button(icon="bookmark_add", on_click=preset_dialog.open).props("flat").tooltip(
                    "Save as Preset"
                ).classes("text-gray-400 hover:text-purple-400")

    global basic_settings_component, parameter_plots_component

    with ui.row().classes("w-full max-w-7xl mx-auto p-4 gap-4"):
        with ui.column().classes("w-3/5 gap-4"):
            with ui.card().classes("w-full bg-gradient-to-r from-cyan-900/20 to-purple-900/20"):
                ui.label(
                    "Explore the Fermi Paradox through Monte Carlo simulation of "
                    "galactic civilizations, hazards, and the Great Filter."
                ).classes("text-gray-300 text-center")
                with ui.row().classes("w-full justify-center gap-4 mt-2"):
                    ui.badge("Drake Equation", color="cyan").props("outline")
                    ui.badge("Kardashev Scale", color="purple").props("outline")
                    ui.badge("Great Filter", color="red").props("outline")

            PresetSelector(on_select=on_preset_select)

            basic_settings_component = BasicSettings(on_change=refresh_plots)

            with ui.expansion("Advanced Settings", icon="tune", value=False).classes(
                "w-full bg-gray-800"
            ):
                ui.label(
                    "Fine-tune all simulation parameters. Changes apply immediately."
                ).classes("text-gray-500 text-sm mb-4")
                ConfigPanels(on_change=refresh_plots)

            results_dashboard = ResultsDashboard()

            def on_simulation_complete():
                if app_state.results and app_state.results.get("simulation"):
                    results_dashboard.show_results(app_state.results["simulation"])

            sim_runner = SimulationRunner()
            sim_runner.on_complete = on_simulation_complete

        with ui.column().classes("w-2/5"):
            parameter_plots_component = ParameterPlots()

    with ui.footer().classes("bg-gray-900/50 border-t border-gray-700/50"):
        with ui.row().classes("w-full max-w-6xl mx-auto items-center px-4 py-2"):
            ui.label("Great Silence v0.1.0").classes("text-gray-500 text-xs")
            ui.space()
            with ui.row().classes("gap-4"):
                ui.link(
                    "Documentation",
                    "https://github.com/grburgess/great_silence/blob/main/md_docs/README.md",
                    new_tab=True,
                ).classes("text-gray-500 text-xs hover:text-cyan-400")
                ui.link(
                    "GitHub",
                    "https://github.com/grburgess/great_silence",
                    new_tab=True,
                ).classes("text-gray-500 text-xs hover:text-cyan-400")


def run_app(host: str = "127.0.0.1", port: int = 8080, reload: bool = False):
    """Run the web application."""
    ui.run(
        title="Great Silence - Galactic Civilization Simulator",
        host=host,
        port=port,
        reload=reload,
        dark=True,
        favicon="🌌",
    )


if __name__ == "__main__":
    run_app()
