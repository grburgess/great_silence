"""Simulation runner component with progress bar and live stats."""

from nicegui import ui, run
import asyncio
import time
from typing import Optional

from ..state import app_state, SimulationEvent


class SimulationRunner:
    """Component for running simulations with progress feedback."""

    def __init__(self):
        self._run_button = None
        self._cancel_button = None
        self._progress_bar = None
        self._progress_label = None
        self._stats_container = None
        self._events_container = None
        self._is_cancelled = False
        self._timer = None
        self._build()

    def _build(self) -> None:
        with ui.card().classes("w-full"):
            ui.label("🚀 Run Simulation").classes("text-lg font-semibold text-gray-300 mb-4")

            with ui.row().classes("w-full gap-4 items-center"):
                self._run_button = (
                    ui.button("▶ Run Simulation", on_click=self._start_simulation)
                    .classes("bg-green-700 hover:bg-green-600 text-white px-8 py-2")
                    .props("size=lg")
                )
                self._cancel_button = (
                    ui.button("⏹ Cancel", on_click=self._cancel_simulation)
                    .classes("bg-red-700 hover:bg-red-600 text-white")
                    .props("size=lg")
                )
                self._cancel_button.visible = False

            with ui.column().classes("w-full gap-2 mt-4") as progress_section:
                self._progress_section = progress_section
                self._progress_section.visible = False

                with ui.row().classes("w-full items-center gap-4"):
                    self._progress_bar = ui.linear_progress(value=0, show_value=False).classes(
                        "flex-grow"
                    )
                    self._progress_label = ui.label("0%").classes(
                        "text-cyan-400 font-mono w-20 text-right"
                    )

                with ui.row().classes("w-full gap-8 mt-2"):
                    self._time_label = ui.label("⏱️ 0.0s").classes("text-gray-400 text-sm")
                    self._sim_time_label = ui.label("📅 0.0 Gyr").classes("text-gray-400 text-sm")
                    self._rate_label = ui.label("⚡ 0 it/s").classes("text-gray-400 text-sm")

            with ui.card().classes("w-full mt-4 bg-gray-900") as stats_card:
                self._stats_card = stats_card
                self._stats_card.visible = False

                ui.label("📊 Live Statistics").classes("text-sm font-semibold text-gray-400 mb-2")

                with ui.row().classes("w-full gap-8"):
                    with ui.column().classes("gap-1"):
                        ui.label("Civilizations").classes("text-xs text-gray-500")
                        self._active_civs_label = ui.label("0").classes(
                            "text-2xl font-bold text-green-400"
                        )
                        ui.label("active").classes("text-xs text-gray-500")

                    with ui.column().classes("gap-1"):
                        ui.label("Total Emerged").classes("text-xs text-gray-500")
                        self._total_civs_label = ui.label("0").classes(
                            "text-2xl font-bold text-blue-400"
                        )
                        ui.label("civilizations").classes("text-xs text-gray-500")

                    with ui.column().classes("gap-1"):
                        ui.label("Extinctions").classes("text-xs text-gray-500")
                        self._extinctions_label = ui.label("0").classes(
                            "text-2xl font-bold text-red-400"
                        )
                        ui.label("deaths").classes("text-xs text-gray-500")

                    with ui.column().classes("gap-1"):
                        ui.label("Probes").classes("text-xs text-gray-500")
                        self._probes_label = ui.label("0").classes(
                            "text-2xl font-bold text-purple-400"
                        )
                        ui.label("in flight").classes("text-xs text-gray-500")

            with ui.card().classes("w-full mt-4 bg-gray-900") as events_card:
                self._events_card = events_card
                self._events_card.visible = False

                ui.label("📡 Event Feed").classes("text-sm font-semibold text-gray-400 mb-2")
                self._events_container = ui.column().classes("w-full gap-1 max-h-40 overflow-auto")

    async def _start_simulation(self) -> None:
        self._is_cancelled = False
        self._run_button.visible = False
        self._cancel_button.visible = True
        self._progress_section.visible = True
        self._stats_card.visible = True
        self._events_card.visible = True

        app_state.reset_progress()
        app_state.progress.is_running = True

        self._events_container.clear()

        start_time = time.time()

        try:
            from great_silence import GalaxySimulation

            config = app_state.config
            config.simulation.save_snapshots = True

            sim = GalaxySimulation(config)
            app_state.simulation = sim

            await run.io_bound(sim.initialize)

            self._add_event(0.0, "init", "🌌 Galaxy initialized with {:,} stars".format(
                config.galaxy.total_stars
            ))

            total_steps = int(
                config.simulation.simulation_duration_gyr * 1000
                / config.simulation.time_step_myr
            )
            step = 0
            last_update = time.time()
            last_civs = 0
            last_extinctions = 0

            while sim.current_time_gyr < config.simulation.simulation_duration_gyr:
                if self._is_cancelled:
                    self._add_event(sim.current_time_gyr, "cancel", "⏹️ Simulation cancelled")
                    break

                await run.io_bound(sim.step)
                step += 1

                now = time.time()
                if now - last_update > 0.3:
                    elapsed = now - start_time
                    progress = sim.current_time_gyr / config.simulation.simulation_duration_gyr
                    rate = step / elapsed if elapsed > 0 else 0

                    self._progress_bar.value = progress
                    self._progress_label.text = f"{progress * 100:.1f}%"
                    self._time_label.text = f"⏱️ {elapsed:.1f}s"
                    self._sim_time_label.text = f"📅 {sim.current_time_gyr:.2f} Gyr"
                    self._rate_label.text = f"⚡ {rate:.0f} it/s"

                    active = len([c for c in sim.civilizations if c.is_active])
                    total = len(sim.civilizations)
                    extinctions = total - active
                    probes = sum(
                        len(c.active_probes) for c in sim.civilizations if hasattr(c, "active_probes")
                    )

                    self._active_civs_label.text = str(active)
                    self._total_civs_label.text = str(total)
                    self._extinctions_label.text = str(extinctions)
                    self._probes_label.text = str(probes)

                    if total > last_civs:
                        new_civs = total - last_civs
                        self._add_event(
                            sim.current_time_gyr,
                            "emergence",
                            f"🌟 {new_civs} new civilization(s) emerged",
                        )
                        last_civs = total

                    if extinctions > last_extinctions:
                        new_deaths = extinctions - last_extinctions
                        self._add_event(
                            sim.current_time_gyr,
                            "extinction",
                            f"💀 {new_deaths} civilization(s) went extinct",
                        )
                        last_extinctions = extinctions

                    last_update = now

            if not self._is_cancelled:
                self._progress_bar.value = 1.0
                self._progress_label.text = "100%"
                self._add_event(
                    sim.current_time_gyr, "complete", "✅ Simulation complete!"
                )

            app_state.results = {
                "simulation": sim,
                "total_civilizations": len(sim.civilizations),
                "active_civilizations": len([c for c in sim.civilizations if c.is_active]),
                "elapsed_time": time.time() - start_time,
            }

        except Exception as e:
            self._add_event(0.0, "error", f"❌ Error: {str(e)}")
            app_state.progress.error_message = str(e)

        finally:
            app_state.progress.is_running = False
            self._run_button.visible = True
            self._cancel_button.visible = False

    def _cancel_simulation(self) -> None:
        self._is_cancelled = True

    def _add_event(self, time_gyr: float, event_type: str, description: str) -> None:
        colors = {
            "init": "text-blue-400",
            "emergence": "text-green-400",
            "extinction": "text-red-400",
            "hazard": "text-orange-400",
            "complete": "text-cyan-400",
            "cancel": "text-yellow-400",
            "error": "text-red-500",
        }
        color = colors.get(event_type, "text-gray-400")

        with self._events_container:
            with ui.row().classes("w-full gap-2 items-center"):
                ui.label(f"[{time_gyr:.2f} Gyr]").classes("text-xs text-gray-500 font-mono w-20")
                ui.label(description).classes(f"text-sm {color}")

        app_state.add_event(SimulationEvent(time_gyr, event_type, description))
