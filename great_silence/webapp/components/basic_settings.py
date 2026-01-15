"""Basic settings panel with essential simulation parameters."""

from nicegui import ui
from typing import Callable, Optional

from ..state import app_state


class BasicSettings:
    """Component for basic simulation settings."""

    def __init__(self, on_change: Optional[Callable[[], None]] = None):
        self.on_change = on_change
        self._build()

    def _build(self) -> None:
        with ui.expansion("Basic Settings", icon="settings", value=True).classes(
            "w-full bg-gray-800"
        ):
            with ui.column().classes("w-full gap-4 p-2"):
                self._create_stars_slider()
                self._create_duration_slider()
                self._create_seed_input()
                self._create_monte_carlo_toggle()

    def _create_stars_slider(self) -> None:
        with ui.row().classes("w-full items-center gap-4"):
            ui.label("Stars:").classes("w-24 text-gray-300")
            slider = ui.slider(
                min=10000, max=500000, step=10000, value=app_state.config.galaxy.total_stars
            ).classes("flex-grow")
            label = ui.label(f"{app_state.config.galaxy.total_stars:,}").classes(
                "w-24 text-right text-cyan-400 font-mono"
            )

            def on_stars_change(e):
                app_state.update_galaxy_param("total_stars", int(e.value))
                label.text = f"{int(e.value):,}"
                if self.on_change:
                    self.on_change()

            slider.on("update:model-value", on_stars_change)

        ui.label("Number of stars to simulate in the galaxy").classes(
            "text-xs text-gray-500 ml-28"
        )

    def _create_duration_slider(self) -> None:
        with ui.row().classes("w-full items-center gap-4"):
            ui.label("Duration:").classes("w-24 text-gray-300")
            slider = ui.slider(
                min=1.0,
                max=15.0,
                step=0.5,
                value=app_state.config.simulation.simulation_duration_gyr,
            ).classes("flex-grow")
            label = ui.label(
                f"{app_state.config.simulation.simulation_duration_gyr:.1f} Gyr"
            ).classes("w-24 text-right text-cyan-400 font-mono")

            def on_duration_change(e):
                app_state.update_simulation_param("simulation_duration_gyr", float(e.value))
                label.text = f"{float(e.value):.1f} Gyr"
                if self.on_change:
                    self.on_change()

            slider.on("update:model-value", on_duration_change)

        ui.label("Simulation time span in billions of years").classes(
            "text-xs text-gray-500 ml-28"
        )

    def _create_seed_input(self) -> None:
        with ui.row().classes("w-full items-center gap-4"):
            ui.label("Random Seed:").classes("w-24 text-gray-300")
            seed_input = (
                ui.number(
                    value=app_state.config.simulation.random_seed,
                    min=0,
                    max=999999,
                    step=1,
                    format="%.0f",
                )
                .classes("w-32")
                .props("dense outlined dark")
            )

            def on_seed_change(e):
                if e.value is not None:
                    app_state.update_simulation_param("random_seed", int(e.value))
                    if self.on_change:
                        self.on_change()

            seed_input.on("update:model-value", on_seed_change)

            ui.button(
                icon="casino",
                on_click=lambda: self._randomize_seed(seed_input),
            ).props("flat dense").tooltip("Randomize seed")

        ui.label("For reproducible simulations").classes("text-xs text-gray-500 ml-28")

    def _randomize_seed(self, seed_input) -> None:
        import random

        new_seed = random.randint(0, 999999)
        seed_input.value = new_seed
        app_state.update_simulation_param("random_seed", new_seed)
        if self.on_change:
            self.on_change()

    def _create_monte_carlo_toggle(self) -> None:
        with ui.row().classes("w-full items-center gap-4"):
            ui.label("Monte Carlo:").classes("w-24 text-gray-300")

            mc_enabled = ui.switch(value=False).classes("text-cyan-400")
            mc_count = (
                ui.number(value=10, min=2, max=1000, step=1, format="%.0f")
                .classes("w-20")
                .props("dense outlined dark")
            )
            mc_count.visible = False
            ui.label("realizations").classes("text-gray-400 text-sm")

            def on_mc_toggle(e):
                mc_count.visible = e.value
                if e.value:
                    app_state.update_simulation_param("num_realizations", int(mc_count.value))
                else:
                    app_state.update_simulation_param("num_realizations", 1)
                if self.on_change:
                    self.on_change()

            def on_mc_count_change(e):
                if e.value is not None and mc_enabled.value:
                    app_state.update_simulation_param("num_realizations", int(e.value))
                    if self.on_change:
                        self.on_change()

            mc_enabled.on("update:model-value", on_mc_toggle)
            mc_count.on("update:model-value", on_mc_count_change)

        ui.label("Run multiple simulations for statistical analysis").classes(
            "text-xs text-gray-500 ml-28"
        )
