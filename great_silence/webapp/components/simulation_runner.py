"""Simulation runner component with progress bar and live stats."""

import asyncio
import time
from threading import Lock
from typing import List, Tuple

from nicegui import run, ui

from ..state import SimulationEvent, app_state


class SimulationRunner:
    """Component for running simulations with progress feedback."""

    _UPDATE_INTERVAL = 0.3
    _MAX_EVENTS = 200

    def __init__(self):
        self._run_button = None
        self._cancel_button = None
        self._progress_bar = None
        self._progress_label = None
        self._stats_container = None
        self._events_log = None
        self._is_cancelled = False
        self._simulation_done = False
        self._simulation_error = None
        self.on_complete = None
        self._events_list: List[Tuple[float, str, str, str]] = []
        self._events_lock = Lock()
        self._displayed_event_count = 0
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
                    self._rate_label = ui.label("⚡ -- it/s").classes("text-gray-400 text-sm")

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
                self._events_log = ui.log(max_lines=30).classes("w-full h-40 bg-gray-950 text-sm")

    async def _start_simulation(self) -> None:
        self._is_cancelled = False
        self._simulation_done = False
        self._simulation_error = None
        self._run_button.visible = False
        self._cancel_button.visible = True
        self._progress_section.visible = True
        self._stats_card.visible = True
        self._events_card.visible = True

        app_state.reset_progress()
        app_state.progress.is_running = True

        with self._events_lock:
            self._events_list = []
            self._displayed_event_count = 0
        self._events_log.clear()
        self._start_time = time.time()
        self._last_civs = 0
        self._last_extinctions = 0

        from great_silence import GalaxySimulation

        config = app_state.config
        config.simulation.save_snapshots = True

        self._sim = GalaxySimulation(config)
        app_state.simulation = self._sim

        self._add_event(
            0.0, "init", f"🌌 Initializing galaxy with {config.galaxy.total_stars:,} stars..."
        )
        self._render_new_events()

        sim_task = asyncio.ensure_future(run.io_bound(self._sim.run, verbose=False))

        while not sim_task.done():
            if self._is_cancelled:
                return
            self._update_progress_display()
            await asyncio.sleep(self._UPDATE_INTERVAL)

        try:
            sim_task.result()
            self._simulation_done = True
        except Exception as e:
            self._simulation_error = str(e)
            self._simulation_done = True

        if self._is_cancelled:
            return

        self._update_progress_display()

        if self._simulation_error:
            self._add_event(0.0, "error", f"❌ Error: {self._simulation_error}")
        else:
            self._progress_bar.value = 1.0
            self._progress_label.text = "100%"
            active = len([c for c in self._sim.civilizations if c.is_active])
            total = len(self._sim.civilizations)
            final_gyr = (
                self._sim.current_time_myr / 1000.0 if hasattr(self._sim, "current_time_myr") else 0
            )
            self._add_event(
                final_gyr,
                "complete",
                f"✅ Complete! {total} civilizations emerged, {active} survived",
            )

        self._render_new_events()
        self._finish_simulation()

    def _update_progress_display(self) -> None:
        if self._is_cancelled:
            return

        try:
            elapsed = time.time() - self._start_time
            total_gyr = app_state.config.simulation.simulation_duration_gyr
            current_myr = (
                self._sim.current_time_myr if hasattr(self._sim, "current_time_myr") else 0
            )
            current_gyr = current_myr / 1000.0

            progress = min(current_gyr / total_gyr, 1.0) if total_gyr > 0 else 0

            self._progress_bar.value = progress
            self._progress_label.text = f"{progress * 100:.1f}%"
            self._time_label.text = f"⏱️ {elapsed:.1f}s"
            self._sim_time_label.text = f"📅 {current_gyr:.2f} Gyr"

            if hasattr(self._sim, "_step_count") and elapsed > 0:
                rate = self._sim._step_count / elapsed
                self._rate_label.text = f"⚡ {rate:.0f} it/s"

            active = len([c for c in self._sim.civilizations if c.is_active])
            total = len(self._sim.civilizations)
            extinctions = total - active
            probes = sum(
                len(c.active_probes) for c in self._sim.civilizations if hasattr(c, "active_probes")
            )

            self._active_civs_label.text = str(active)
            self._total_civs_label.text = str(total)
            self._extinctions_label.text = str(extinctions)
            self._probes_label.text = str(probes)

            if total > self._last_civs:
                new_civs = total - self._last_civs
                self._add_event(
                    current_gyr, "emergence", f"🌟 {new_civs} new civilization(s) emerged"
                )
                self._last_civs = total

            if extinctions > self._last_extinctions:
                new_deaths = extinctions - self._last_extinctions
                self._add_event(
                    current_gyr, "extinction", f"💀 {new_deaths} civilization(s) went extinct"
                )
                self._last_extinctions = extinctions

            self._render_new_events()

        except Exception:
            pass

    def _finish_simulation(self) -> None:
        app_state.progress.is_running = False
        app_state.results = {
            "simulation": self._sim,
            "total_civilizations": len(self._sim.civilizations) if self._sim else 0,
            "active_civilizations": (
                len([c for c in self._sim.civilizations if c.is_active]) if self._sim else 0
            ),
            "elapsed_time": time.time() - self._start_time,
        }
        self._run_button.visible = True
        self._cancel_button.visible = False

        if self.on_complete and not self._simulation_error and not self._is_cancelled:
            try:
                self.on_complete()
            except Exception:
                pass

    def _cancel_simulation(self) -> None:
        """Cancel the simulation and reset UI."""
        self._is_cancelled = True

        if self._sim:
            current_gyr = (
                self._sim.current_time_myr / 1000.0
                if hasattr(self._sim, "current_time_myr")
                else 0.0
            )
            self._add_event(
                current_gyr,
                "cancel",
                "⏹️ Simulation cancelled (background thread may still be running)",
            )
            self._render_new_events()

        app_state.progress.is_running = False
        self._run_button.visible = True
        self._cancel_button.visible = False

        ui.notify("Simulation cancelled", type="warning")

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

        with self._events_lock:
            self._events_list.append((time_gyr, event_type, description, color))

        app_state.add_event(SimulationEvent(time_gyr, event_type, description))

    def _render_new_events(self) -> None:
        """Render only new events that haven't been displayed yet."""
        with self._events_lock:
            new_events = self._events_list[self._displayed_event_count :]
            self._displayed_event_count = len(self._events_list)
            if len(self._events_list) > self._MAX_EVENTS:
                self._events_list = self._events_list[-self._MAX_EVENTS :]
                self._displayed_event_count = len(self._events_list)

        for time_gyr, event_type, description, color in new_events[-self._MAX_EVENTS :]:
            self._events_log.push(f"[{time_gyr:6.2f} Gyr] {description}")
