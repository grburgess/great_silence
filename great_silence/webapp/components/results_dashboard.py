"""Results dashboard with Three.js visualization embed and statistics."""

import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional

from nicegui import app, run, ui

from ..state import app_state

VIZ_ROOT = Path(tempfile.gettempdir()) / "great_silence_viz"
VIZ_ROOT.mkdir(parents=True, exist_ok=True)
app.add_static_files("/viz", str(VIZ_ROOT))


def _prune_viz_dirs(root: Path, keep: int = 3, exclude: Optional[Path] = None) -> None:
    run_dirs = [p for p in root.iterdir() if p.is_dir() and p != exclude]
    run_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for old in run_dirs[keep:]:
        shutil.rmtree(old, ignore_errors=True)


class ResultsDashboard:
    """Component for displaying simulation results with 3D visualization."""

    def __init__(self):
        self._container = None
        self._viz_html_path = None
        self._fullscreen_dialog = None
        self._build()

    def _build(self) -> None:
        with ui.card().classes("w-full") as container:
            self._container = container
            self._container.visible = False

            ui.label("Results").classes("gs-eyebrow text-gray-300 mb-4").style(
                "font-size: 0.85rem;"
            )

            with ui.tabs().classes("w-full") as tabs:
                self._stats_tab = ui.tab("Statistics", icon="analytics")
                self._viz_tab = ui.tab("3D Visualization", icon="view_in_ar")
                self._export_tab = ui.tab("Export", icon="download")

            with ui.tab_panels(tabs, value=self._stats_tab).classes("w-full"):
                with ui.tab_panel(self._stats_tab):
                    self._stats_container = ui.column().classes("w-full gap-4")

                with ui.tab_panel(self._viz_tab):
                    self._viz_container = ui.column().classes("w-full gap-4")

                with ui.tab_panel(self._export_tab):
                    self._export_container = ui.column().classes("w-full gap-4")

    def show_results(self, simulation) -> None:
        """Display results for a completed simulation."""
        self._container.visible = True
        self._populate_stats(simulation)
        self._setup_visualization(simulation)
        self._setup_exports(simulation)

    def _populate_stats(self, sim) -> None:
        """Populate statistics tab with simulation results."""
        self._stats_container.clear()

        with self._stats_container:
            active = len([c for c in sim.civilizations if c.is_active])
            total = len(sim.civilizations)
            extinct = total - active

            with ui.row().classes("w-full gap-8 flex-wrap"):
                self._stat_card("Total Emerged", str(total), "🌟", "blue")
                self._stat_card("Active", str(active), "✅", "green")
                self._stat_card("Extinct", str(extinct), "💀", "red")

                probes = sum(
                    len(c.active_probes) + len(c.archived_probes)
                    for c in sim.civilizations
                    if hasattr(c, "active_probes")
                )
                self._stat_card("Total Probes", str(probes), "🚀", "purple")

            if total > 0:
                ui.separator().classes("my-4")
                ui.label("Extinction Causes").classes("gs-eyebrow text-gray-400")

                death_causes = {}
                for c in sim.civilizations:
                    if not c.is_active and c.death_cause:
                        cause = c.death_cause
                        death_causes[cause] = death_causes.get(cause, 0) + 1

                if death_causes:
                    with ui.row().classes("w-full gap-4 flex-wrap"):
                        cause_colors = {
                            "self_destruction": "orange",
                            "supernova": "red",
                            "grb": "cyan",
                            "ns_merger": "pink",
                            "old_age": "gray",
                            "colonial_war": "yellow",
                        }
                        for cause, count in sorted(death_causes.items(), key=lambda x: -x[1]):
                            color = cause_colors.get(cause, "gray")
                            pct = count / extinct * 100 if extinct > 0 else 0
                            with ui.card().classes(f"gs-stat bg-{color}-900/30 p-3"):
                                ui.label(cause.replace("_", " ").title()).classes(
                                    f"gs-eyebrow text-{color}-400"
                                )
                                ui.label(f"{count} ({pct:.1f}%)").classes(
                                    "gs-metric text-white text-lg"
                                )
                else:
                    ui.label("No extinctions recorded").classes("text-gray-500 italic")

                ui.separator().classes("my-4")
                ui.label("Kardashev Distribution").classes("gs-eyebrow text-gray-400")

                if total > 0:
                    k_levels = [c.kardashev_scale for c in sim.civilizations]
                    avg_k = sum(k_levels) / len(k_levels)
                    max_k = max(k_levels)

                    with ui.row().classes("w-full gap-4"):
                        with ui.card().classes("gs-stat bg-gray-800 p-3"):
                            ui.label("Average K-Level").classes("gs-eyebrow text-gray-400")
                            ui.label(f"{avg_k:.2f}").classes(
                                "gs-metric text-cyan-400 text-xl font-bold"
                            )
                        with ui.card().classes("gs-stat bg-gray-800 p-3"):
                            ui.label("Maximum K-Level").classes("gs-eyebrow text-gray-400")
                            ui.label(f"{max_k:.2f}").classes(
                                "gs-metric text-purple-400 text-xl font-bold"
                            )

                        type_counts = {"Type 0": 0, "Type I": 0, "Type II": 0, "Type III": 0}
                        for k in k_levels:
                            if k < 1.0:
                                type_counts["Type 0"] += 1
                            elif k < 2.0:
                                type_counts["Type I"] += 1
                            elif k < 3.0:
                                type_counts["Type II"] += 1
                            else:
                                type_counts["Type III"] += 1

                        for type_name, count in type_counts.items():
                            if count > 0:
                                with ui.card().classes("gs-stat bg-gray-800 p-3"):
                                    ui.label(type_name).classes("gs-eyebrow text-gray-400")
                                    ui.label(str(count)).classes("gs-metric text-white text-lg")

    def _stat_card(self, label: str, value: str, icon: str, color: str) -> None:
        """Create a statistics card."""
        with ui.card().classes(f"gs-stat bg-{color}-900/30 p-4"):
            with ui.row().classes("items-center gap-3"):
                ui.label(icon).classes("text-3xl")
                with ui.column().classes("gap-1"):
                    ui.label(label).classes(f"gs-eyebrow text-{color}-400")
                    ui.label(value).classes("gs-metric text-white text-3xl font-bold")

    def _setup_visualization(self, sim) -> None:
        """Setup 3D visualization tab."""
        self._viz_container.clear()

        with self._viz_container:
            ui.label("Interactive 3D Galaxy Visualization").classes("text-gray-400 mb-2")

            with ui.row().classes("w-full gap-4"):
                self._generate_btn = ui.button(
                    "Generate Visualization",
                    icon="view_in_ar",
                    on_click=lambda: self._generate_viz(sim),
                ).classes("bg-cyan-700 hover:bg-cyan-600")

                self._fullscreen_btn = ui.button(
                    "Fullscreen",
                    icon="fullscreen",
                    on_click=self._open_fullscreen,
                ).classes("bg-purple-700 hover:bg-purple-600")
                self._fullscreen_btn.visible = False

            self._viz_frame_container = ui.column().classes("w-full mt-4")

            self._fullscreen_dialog = ui.dialog().classes("max-w-none").props("maximized")
            with self._fullscreen_dialog, ui.card().classes("w-full h-full bg-black"):
                with ui.row().classes("w-full justify-end p-2"):
                    ui.button(icon="close", on_click=self._fullscreen_dialog.close).props(
                        "flat round"
                    ).classes("text-white")
                self._fullscreen_frame = ui.html("", sanitize=False).classes("w-full h-full")

    async def _generate_viz(self, sim) -> None:
        """Generate the Three.js visualization."""
        import traceback

        from great_silence.visualization.threejs import export_html

        self._generate_btn.disable()
        self._viz_frame_container.clear()
        with self._viz_frame_container, ui.row().classes("items-center gap-3 mt-4"):
            ui.spinner(size="lg", color="cyan")
            ui.label("Generating visualization...").classes("text-gray-400")

        try:
            run_dir = VIZ_ROOT / f"run_{int(time.time() * 1000)}"
            run_dir.mkdir(parents=True, exist_ok=True)
            self._viz_html_path = str(run_dir / "visualization.html")

            await run.io_bound(
                export_html,
                sim,
                self._viz_html_path,
                animated=True,
                show_trajectories=True,
                show_spheres=True,
                show_hazards=True,
            )

            _prune_viz_dirs(VIZ_ROOT, keep=3, exclude=run_dir)

            viz_url = f"/viz/{run_dir.name}/visualization.html"

            self._viz_frame_container.clear()
            with self._viz_frame_container:
                ui.html(
                    f'<iframe src="{viz_url}" '
                    f'style="width: 100%; height: 600px; border: 1px solid #333; border-radius: 8px;">'
                    f"</iframe>",
                    sanitize=False,
                )

            self._fullscreen_frame.content = (
                f'<iframe src="{viz_url}" '
                f'style="width: 100%; height: calc(100vh - 80px); border: none;"></iframe>'
            )
            self._fullscreen_btn.visible = True

            ui.notify("Visualization generated!", type="positive")

        except Exception as e:
            traceback.print_exc()
            self._viz_frame_container.clear()
            ui.notify(f"Error generating visualization: {e}", type="negative")
        finally:
            self._generate_btn.enable()

    def _open_fullscreen(self) -> None:
        """Open the fullscreen visualization dialog."""
        if self._fullscreen_dialog:
            self._fullscreen_dialog.open()

    def _setup_exports(self, sim) -> None:
        """Setup export options tab."""
        self._export_container.clear()

        with self._export_container:
            ui.label("Export simulation results and visualizations").classes("text-gray-400 mb-4")

            with ui.column().classes("w-full gap-4"):
                with ui.card().classes("w-full bg-gray-800 p-4"):
                    ui.label("Export Visualization HTML").classes("font-semibold text-gray-300")
                    ui.label("Save the 3D visualization as a standalone HTML file").classes(
                        "text-gray-500 text-sm mb-2"
                    )

                    with ui.row().classes("gap-4"):
                        self._html_path_input = (
                            ui.input(value="galaxy_visualization.html", placeholder="filename.html")
                            .classes("w-64")
                            .props("dense outlined dark")
                        )
                        ui.button(
                            "Export HTML",
                            icon="html",
                            on_click=lambda: self._export_html(sim),
                        ).classes("bg-orange-700 hover:bg-orange-600")

                with ui.card().classes("w-full bg-gray-800 p-4"):
                    ui.label("Export Configuration").classes("font-semibold text-gray-300")
                    ui.label("Save the current configuration as a YAML file").classes(
                        "text-gray-500 text-sm mb-2"
                    )

                    with ui.row().classes("gap-4"):
                        self._yaml_path_input = (
                            ui.input(value="simulation_config.yaml", placeholder="filename.yaml")
                            .classes("w-64")
                            .props("dense outlined dark")
                        )
                        ui.button(
                            "Export YAML",
                            icon="description",
                            on_click=self._export_yaml,
                        ).classes("bg-green-700 hover:bg-green-600")

                with ui.card().classes("w-full bg-gray-800 p-4"):
                    ui.label("Export Data (HDF5)").classes("font-semibold text-gray-300")
                    ui.label("Save simulation data for later analysis").classes(
                        "text-gray-500 text-sm mb-2"
                    )

                    with ui.row().classes("gap-4"):
                        self._hdf5_path_input = (
                            ui.input(value="simulation_data.h5", placeholder="filename.h5")
                            .classes("w-64")
                            .props("dense outlined dark")
                        )
                        ui.button(
                            "Export HDF5",
                            icon="storage",
                            on_click=lambda: self._export_hdf5(sim),
                        ).classes("bg-blue-700 hover:bg-blue-600")

    async def _export_html(self, sim) -> None:
        """Export visualization as HTML."""
        try:
            from great_silence.visualization.threejs import export_html

            output_path = self._html_path_input.value
            if not output_path.endswith(".html"):
                output_path += ".html"

            output_dir = Path(app_state.config.simulation.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            full_path = output_dir / output_path

            await run.io_bound(export_html, sim, str(full_path), animated=True)
            ui.notify(f"Exported to {full_path}", type="positive")

        except Exception as e:
            ui.notify(f"Export failed: {e}", type="negative")

    def _export_yaml(self) -> None:
        """Export configuration as YAML."""
        try:
            output_path = self._yaml_path_input.value
            if not output_path.endswith(".yaml"):
                output_path += ".yaml"

            output_dir = Path(app_state.config.simulation.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            full_path = output_dir / output_path

            app_state.config.to_yaml(str(full_path))
            ui.notify(f"Exported to {full_path}", type="positive")

        except Exception as e:
            ui.notify(f"Export failed: {e}", type="negative")

    def _export_hdf5(self, sim) -> None:
        """Export simulation data as HDF5."""
        try:
            from great_silence.notebook import save_simulation_hdf5

            output_path = self._hdf5_path_input.value
            if not output_path.endswith(".h5"):
                output_path += ".h5"

            output_dir = Path(app_state.config.simulation.output_directory)
            output_dir.mkdir(parents=True, exist_ok=True)
            full_path = output_dir / output_path

            save_simulation_hdf5(sim, str(full_path))
            ui.notify(f"Exported to {full_path}", type="positive")

        except Exception as e:
            ui.notify(f"Export failed: {e}", type="negative")
