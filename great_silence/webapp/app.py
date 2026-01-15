"""Main NiceGUI web application for Great Silence simulations."""

from nicegui import ui, app
from pathlib import Path

from .state import app_state
from .components import PresetSelector, BasicSettings, SimulationRunner, ConfigPanels, ResultsDashboard


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
    </style>
    """)


def on_preset_select(preset_name: str) -> None:
    """Handle preset selection."""
    app_state.apply_preset(preset_name)
    ui.notify(f"Applied '{preset_name}' preset", type="positive", position="top")


@ui.page("/")
def main_page():
    """Main application page."""
    apply_dark_theme()
    ui.dark_mode().enable()

    with ui.header().classes(
        "bg-gray-900/80 backdrop-blur-sm border-b border-gray-700/50 items-center"
    ):
        with ui.row().classes("w-full max-w-6xl mx-auto items-center px-4"):
            ui.label("🌌").classes("text-3xl")
            ui.label("GREAT SILENCE").classes(
                "text-2xl font-bold tracking-wider text-transparent bg-clip-text "
                "bg-gradient-to-r from-cyan-400 to-purple-500"
            )
            ui.space()
            ui.label("Galactic Civilization Simulator").classes("text-gray-400 text-sm")

    with ui.column().classes("w-full max-w-4xl mx-auto p-6 gap-6"):
        ui.label(
            "Explore the Fermi Paradox through Monte Carlo simulation of "
            "galactic civilizations, hazards, and the Great Filter."
        ).classes("text-gray-400 text-center mb-4")

        PresetSelector(on_select=on_preset_select)

        BasicSettings()

        with ui.expansion("Advanced Settings", icon="tune", value=False).classes(
            "w-full bg-gray-800"
        ):
            ConfigPanels()

        results_dashboard = ResultsDashboard()

        def on_simulation_complete():
            if app_state.results and app_state.results.get("simulation"):
                results_dashboard.show_results(app_state.results["simulation"])

        sim_runner = SimulationRunner()
        sim_runner.on_complete = on_simulation_complete

    with ui.footer().classes("bg-gray-900/50 border-t border-gray-700/50"):
        with ui.row().classes("w-full max-w-6xl mx-auto items-center px-4 py-2"):
            ui.label("Great Silence v0.1.0").classes("text-gray-500 text-xs")
            ui.space()
            ui.link("GitHub", "https://github.com/grburgess/great_silence", new_tab=True).classes(
                "text-gray-500 text-xs hover:text-cyan-400"
            )


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
