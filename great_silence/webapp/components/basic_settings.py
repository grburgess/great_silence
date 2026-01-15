"""Basic settings panel with essential simulation parameters."""

from nicegui import ui
from typing import Callable, Optional

from ..state import app_state


class BasicSettings:
    """Component for basic simulation settings."""

    def __init__(self, on_change: Optional[Callable[[], None]] = None):
        self.on_change = on_change
        self._stars_slider = None
        self._stars_label = None
        self._duration_slider = None
        self._duration_label = None
        self._seed_input = None
        self._build()
        app_state.on_update(self._sync_from_state)

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
            self._stars_slider = ui.slider(
                min=10000, max=500000, step=10000, value=app_state.config.galaxy.total_stars
            ).classes("flex-grow")
            self._stars_label = ui.label(f"{app_state.config.galaxy.total_stars:,}").classes(
                "w-24 text-right text-cyan-400 font-mono"
            )

            def on_stars_change(e):
                val = e.args if isinstance(e.args, (int, float)) else self._stars_slider.value
                app_state.config.galaxy.total_stars = int(val)
                self._stars_label.text = f"{int(val):,}"
                if self.on_change:
                    self.on_change()

            self._stars_slider.on("update:model-value", on_stars_change)

        ui.label("Number of stars to simulate in the galaxy").classes(
            "text-xs text-gray-500 ml-28"
        )

    def _create_duration_slider(self) -> None:
        with ui.row().classes("w-full items-center gap-4"):
            ui.label("Duration:").classes("w-24 text-gray-300")
            self._duration_slider = ui.slider(
                min=1.0,
                max=15.0,
                step=0.5,
                value=app_state.config.simulation.simulation_duration_gyr,
            ).classes("flex-grow")
            self._duration_label = ui.label(
                f"{app_state.config.simulation.simulation_duration_gyr:.1f} Gyr"
            ).classes("w-24 text-right text-cyan-400 font-mono")

            def on_duration_change(e):
                val = e.args if isinstance(e.args, (int, float)) else self._duration_slider.value
                app_state.config.simulation.simulation_duration_gyr = float(val)
                self._duration_label.text = f"{float(val):.1f} Gyr"
                if self.on_change:
                    self.on_change()

            self._duration_slider.on("update:model-value", on_duration_change)

        ui.label("Simulation time span in billions of years").classes(
            "text-xs text-gray-500 ml-28"
        )

    def _create_seed_input(self) -> None:
        with ui.row().classes("w-full items-center gap-4"):
            ui.label("Random Seed:").classes("w-24 text-gray-300")
            self._seed_input = (
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
                val = e.args if isinstance(e.args, (int, float)) else self._seed_input.value
                if val is not None:
                    app_state.config.simulation.random_seed = int(val)
                    if self.on_change:
                        self.on_change()

            self._seed_input.on("update:model-value", on_seed_change)

            ui.button(
                icon="casino",
                on_click=lambda: self._randomize_seed(),
            ).props("flat dense").tooltip("Randomize seed")

        ui.label("For reproducible simulations").classes("text-xs text-gray-500 ml-28")

    def _randomize_seed(self) -> None:
        import random

        new_seed = random.randint(0, 999999)
        self._seed_input.value = new_seed
        app_state.config.simulation.random_seed = new_seed
        if self.on_change:
            self.on_change()

    def _create_monte_carlo_toggle(self) -> None:
        with ui.row().classes("w-full items-center gap-4"):
            ui.label("Monte Carlo:").classes("w-24 text-gray-300")

            self._mc_enabled = ui.switch(value=False).classes("text-cyan-400")
            self._mc_count = (
                ui.number(value=10, min=2, max=1000, step=1, format="%.0f")
                .classes("w-20")
                .props("dense outlined dark")
            )
            self._mc_count.visible = False
            ui.label("realizations").classes("text-gray-400 text-sm")

            def on_mc_toggle(e):
                val = e.args if isinstance(e.args, bool) else self._mc_enabled.value
                self._mc_count.visible = val
                if val:
                    app_state.config.simulation.num_realizations = int(self._mc_count.value)
                else:
                    app_state.config.simulation.num_realizations = 1
                if self.on_change:
                    self.on_change()

            def on_mc_count_change(e):
                val = e.args if isinstance(e.args, (int, float)) else self._mc_count.value
                if val is not None and self._mc_enabled.value:
                    app_state.config.simulation.num_realizations = int(val)
                    if self.on_change:
                        self.on_change()

            self._mc_enabled.on("update:model-value", on_mc_toggle)
            self._mc_count.on("update:model-value", on_mc_count_change)

        ui.label("Run multiple simulations for statistical analysis").classes(
            "text-xs text-gray-500 ml-28"
        )

    def _sync_from_state(self) -> None:
        """Sync UI widgets from app state (called when preset changes)."""
        try:
            if self._stars_slider is not None:
                self._stars_slider.value = app_state.config.galaxy.total_stars
                self._stars_label.text = f"{app_state.config.galaxy.total_stars:,}"

            if self._duration_slider is not None:
                self._duration_slider.value = app_state.config.simulation.simulation_duration_gyr
                self._duration_label.text = (
                    f"{app_state.config.simulation.simulation_duration_gyr:.1f} Gyr"
                )

            if self._seed_input is not None:
                self._seed_input.value = app_state.config.simulation.random_seed
        except Exception:
            pass
