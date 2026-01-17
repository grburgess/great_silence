"""Main NiceGUI web application for Great Silence simulations."""

from nicegui import ui, app
from pathlib import Path
from typing import Callable, Optional

from .state import app_state
from .components import PresetSelector, BasicSettings, SimulationRunner, ConfigPanels, ResultsDashboard, ParameterPlots
from .config_io import create_load_config_dialog, create_save_config_dialog, create_save_preset_dialog
from .themes import SPACE_THEMES, get_theme_css, get_base_css, get_theme_options


class DebouncedCallback:
    """Debounces a callback to only fire after a delay with no new calls."""
    
    def __init__(self, callback: Callable[[], None], delay_seconds: float = 0.3):
        self._callback = callback
        self._delay = delay_seconds
        self._timer: Optional[ui.timer] = None
    
    def __call__(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
        self._timer = ui.timer(self._delay, self._execute, once=True)
    
    def _execute(self) -> None:
        self._timer = None
        self._callback()


def apply_dark_theme(theme_name: str = "deep_space"):
    """Apply dark space theme to the application."""
    base_css = get_base_css()
    theme_css = get_theme_css(theme_name)

    ui.add_head_html(f"""
    <style>
        {base_css}
    </style>
    <style id="theme-styles">
        {theme_css}
    </style>
    """)


def refresh_ui_from_state():
    """Refresh UI components after loading config."""
    app_state._notify_update()
    ui.notify("Configuration loaded - UI updated", type="info")


@ui.page("/")
def main_page():
    """Main application page."""
    apply_dark_theme(app_state.current_theme)
    ui.dark_mode().enable()

    ui.html('<div class="theme-bg-effect"></div>', sanitize=False)

    load_dialog = create_load_config_dialog(on_load_callback=refresh_ui_from_state)
    save_dialog = create_save_config_dialog()
    preset_dialog = create_save_preset_dialog()

    def on_theme_change(theme_name: str):
        """Handle theme change from dropdown."""
        app_state.set_theme(theme_name)
        theme_css = get_theme_css(theme_name)
        escaped_css = theme_css.replace('`', '\\`').replace('${', '\\${')
        ui.run_javascript(f"""
            const styleEl = document.getElementById('theme-styles');
            if (styleEl) {{
                styleEl.textContent = `{escaped_css}`;
            }}
        """)
        theme = SPACE_THEMES.get(theme_name, SPACE_THEMES["deep_space"])
        ui.notify(f"{theme['icon']} {theme['name']} theme applied", type="positive", position="top")

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

            ui.select(
                options={t["value"]: t["label"] for t in get_theme_options()},
                value=app_state.current_theme,
                on_change=lambda e: on_theme_change(e.value),
            ).props("dense dark outlined").classes("w-44").tooltip("Select Theme")

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

    plots_ref = {'component': None}

    def refresh_plots_immediate():
        if plots_ref['component']:
            plots_ref['component'].refresh()

    refresh_plots = DebouncedCallback(refresh_plots_immediate, delay_seconds=0.3)

    def on_preset_select(preset_name: str):
        app_state.apply_preset(preset_name)
        ui.notify(f"Applied '{preset_name}' preset", type="positive", position="top")
        refresh_plots_immediate()

    with ui.element('div').classes("w-full flex flex-row gap-4 p-4").style("max-width: 1800px; margin: 0 auto;"):
        with ui.column().classes("gap-4").style("flex: 1; min-width: 0;"):
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

            BasicSettings(on_change=refresh_plots)

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

        with ui.column().classes("gap-4").style("flex: 1; min-width: 0;"):
            plots_ref['component'] = ParameterPlots()

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
