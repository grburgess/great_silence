"""Interactive widgets for Jupyter notebooks."""

from typing import Optional, Dict, Any
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
import pandas as pd

from great_silence import SimulationConfig, configure_m1_max_threading
from .runners import NotebookSimulationRunner
from .helpers import export_interactive_plot


class SimulationWidget:
    """
    High-level widget for configuring and running simulations.

    Provides preset selector and key parameter overrides.
    """

    def __init__(self):
        """Initialize simulation widget."""
        # Configure threading for M1 Max
        configure_m1_max_threading()

        self.runner = None
        self.results = None

        # Create widgets
        self._create_widgets()
        self._setup_layout()

    def _create_widgets(self):
        """Create all widget components."""
        # Preset selector
        self.preset_selector = widgets.Dropdown(
            options=['moderate', 'optimistic', 'early_filter', 'late_filter', 'rare_earth'],
            value='moderate',
            description='Preset:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='400px')
        )

        # Parameter overrides
        self.num_stars_slider = widgets.IntSlider(
            value=100_000,
            min=10_000,
            max=500_000,
            step=10_000,
            description='Stars:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='500px'),
            readout_format=',d'
        )

        self.duration_slider = widgets.FloatSlider(
            value=10.0,
            min=1.0,
            max=20.0,
            step=1.0,
            description='Duration (Gyr):',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='500px')
        )

        self.seed_input = widgets.IntText(
            value=42,
            description='Random Seed:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='250px')
        )

        # Monte Carlo option
        self.monte_carlo_checkbox = widgets.Checkbox(
            value=False,
            description='Monte Carlo mode',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='200px')
        )

        self.num_realizations_slider = widgets.IntSlider(
            value=100,
            min=10,
            max=1000,
            step=10,
            description='Realizations:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='500px'),
            disabled=True
        )

        # Link Monte Carlo checkbox to realizations slider
        def toggle_realizations(change):
            self.num_realizations_slider.disabled = not change['new']

        self.monte_carlo_checkbox.observe(toggle_realizations, names='value')

        # Run button
        self.run_button = widgets.Button(
            description='Run Simulation',
            button_style='success',
            icon='play',
            layout=widgets.Layout(width='200px', height='40px')
        )
        self.run_button.on_click(self._on_run_clicked)

        # Output area
        self.output_area = widgets.Output()

        # Progress indicator
        self.progress_label = widgets.Label(value='Ready')

    def _setup_layout(self):
        """Create widget layout."""
        # Parameter section
        params_box = widgets.VBox([
            widgets.HTML("<h3>Simulation Configuration</h3>"),
            self.preset_selector,
            widgets.HTML("<br><b>Override Parameters:</b>"),
            self.num_stars_slider,
            self.duration_slider,
            self.seed_input,
            widgets.HTML("<br><b>Monte Carlo Options:</b>"),
            self.monte_carlo_checkbox,
            self.num_realizations_slider,
        ])

        # Control section
        controls_box = widgets.VBox([
            widgets.HTML("<h3>Run Simulation</h3>"),
            self.run_button,
            self.progress_label,
        ])

        # Main layout
        self.main_layout = widgets.VBox([
            widgets.HTML("<h2 style='color: #2e86de;'>GalaticBot Simulation Interface</h2>"),
            widgets.HTML("<hr>"),
            params_box,
            widgets.HTML("<br>"),
            controls_box,
            widgets.HTML("<hr>"),
            self.output_area,
        ], layout=widgets.Layout(padding='20px'))

    def display(self):
        """Display the widget interface."""
        from IPython.display import display
        display(self.main_layout)
        return None  # Explicitly return None to prevent output

    def _on_run_clicked(self, button):
        """Handle run button click."""
        # Disable button during run
        self.run_button.disabled = True
        self.progress_label.value = 'Running...'

        # Clear previous output
        with self.output_area:
            clear_output(wait=True)

        try:
            # Create config
            config = self._create_config()

            # Create runner
            self.runner = NotebookSimulationRunner(
                config=config,
                seed=self.seed_input.value
            )

            # Run simulation
            with self.output_area:
                display(HTML("<h3>Simulation Progress</h3>"))

                if self.monte_carlo_checkbox.value:
                    # Monte Carlo mode
                    self.results = self.runner.run_monte_carlo(
                        num_realizations=self.num_realizations_slider.value,
                        verbose=True
                    )
                else:
                    # Single run mode
                    self.results = self.runner.run(verbose=True)

                # Display results
                self._display_results()

            self.progress_label.value = 'Complete!'

        except Exception as e:
            with self.output_area:
                display(HTML(f"<p style='color: red;'><b>Error:</b> {str(e)}</p>"))
            self.progress_label.value = 'Failed'

        finally:
            # Re-enable button
            self.run_button.disabled = False

    def _create_config(self) -> SimulationConfig:
        """Create SimulationConfig from widget values."""
        # Start with preset
        config = SimulationConfig.with_preset(self.preset_selector.value)

        # Override parameters
        config.galaxy.total_stars = self.num_stars_slider.value
        config.simulation.simulation_duration_gyr = self.duration_slider.value

        # Enable snapshots for visualization
        config.simulation.save_snapshots = True
        config.simulation.snapshot_interval_myr = 500.0

        # Monte Carlo settings
        if self.monte_carlo_checkbox.value:
            config.simulation.num_realizations = self.num_realizations_slider.value

        return config

    def _display_results(self):
        """Display simulation results."""
        if self.results is None:
            return

        # Display statistics table
        display(HTML("<h3>Results Summary</h3>"))

        if 'statistics' in self.results:
            summary_table = self.runner.get_summary_table()
            display(summary_table)

        # Quick visualization links
        display(HTML("<br><h4>Available Visualizations:</h4>"))
        display(HTML("""
        <p>Use the following methods to create visualizations:</p>
        <ul>
            <li><code>widget.runner.plot_3d_galaxy()</code> - 3D galaxy view</li>
            <li><code>widget.runner.plot_timeline()</code> - Civilization timeline</li>
            <li><code>widget.runner.plot_extinction_causes()</code> - Death cause breakdown</li>
        </ul>
        """))

    def export_results(self, path: str):
        """
        Export simulation results to HDF5.

        Args:
            path: Output path (without extension)
        """
        if self.runner is None:
            raise ValueError("No simulation to export. Run simulation first.")

        h5_path = self.runner.save(path)
        display(HTML(f"<p style='color: green;'>✓ Results saved to: {h5_path}</p>"))
        return h5_path


class ResultsExplorer:
    """Widget for exploring saved simulation results."""

    def __init__(self, results_path: Optional[str] = None):
        """
        Initialize results explorer.

        Args:
            results_path: Path to HDF5 results file
        """
        self.results_path = results_path
        self.data = None

        # Create widgets first
        self._create_widgets()

        # Then load data if path provided
        if results_path:
            self.load(results_path)

    @classmethod
    def from_directory(cls, directory: str):
        """
        Create explorer with directory file browser.

        Args:
            directory: Directory containing results

        Returns:
            ResultsExplorer instance
        """
        from pathlib import Path

        # Find .h5 files
        h5_files = list(Path(directory).glob("*.h5"))

        if not h5_files:
            raise ValueError(f"No .h5 files found in {directory}")

        # Create file selector
        instance = cls()
        instance.file_selector = widgets.Dropdown(
            options=[str(f) for f in h5_files],
            description='Select file:',
            layout=widgets.Layout(width='500px')
        )

        instance.load_button = widgets.Button(
            description='Load',
            button_style='primary'
        )

        def on_load(button):
            instance.load(instance.file_selector.value)

        instance.load_button.on_click(on_load)

        return instance

    def _create_widgets(self):
        """Create filter widgets."""
        # Status filter
        self.status_filter = widgets.RadioButtons(
            options=['All', 'Active', 'Extinct'],
            value='All',
            description='Status:',
            disabled=True
        )

        # Kardashev filter
        self.kardashev_min = widgets.FloatSlider(
            value=0.0,
            min=0.0,
            max=3.0,
            step=0.1,
            description='Min K-level:',
            disabled=True
        )

        self.kardashev_max = widgets.FloatSlider(
            value=3.0,
            min=0.0,
            max=3.0,
            step=0.1,
            description='Max K-level:',
            disabled=True
        )

        # Apply filters button
        self.apply_button = widgets.Button(
            description='Apply Filters',
            button_style='info',
            disabled=True
        )
        self.apply_button.on_click(self._apply_filters)

        # Output
        self.output = widgets.Output()

    def load(self, path: str):
        """Load results from HDF5 file."""
        from .helpers import load_simulation

        self.results_path = path
        self.data = load_simulation(path)

        # Enable widgets
        self.status_filter.disabled = False
        self.kardashev_min.disabled = False
        self.kardashev_max.disabled = False
        self.apply_button.disabled = False

        with self.output:
            clear_output()
            display(HTML(f"<p style='color: green;'>✓ Loaded: {path}</p>"))
            self._show_summary()

    def _show_summary(self):
        """Display results summary."""
        if self.data is None:
            return

        stats = self.data.get('statistics', {})

        display(HTML("<h3>Simulation Summary</h3>"))
        summary = [
            ('Total Civilizations', stats.get('total_civilizations', 'N/A')),
            ('Active Civilizations', stats.get('active_civilizations', 'N/A')),
            ('Extinct Civilizations', stats.get('extinct_civilizations', 'N/A')),
        ]

        df = pd.DataFrame(summary, columns=['Metric', 'Value'])
        display(df)

    def _apply_filters(self, button):
        """Apply filters and display filtered results."""
        with self.output:
            clear_output()

            if self.data is None:
                display(HTML("<p style='color: red;'>No data loaded</p>"))
                return

            civs = self.data.get('civilizations', [])

            # Apply status filter
            if self.status_filter.value == 'Active':
                civs = [c for c in civs if c['is_active']]
            elif self.status_filter.value == 'Extinct':
                civs = [c for c in civs if not c['is_active']]

            # Apply Kardashev filter
            civs = [c for c in civs
                   if self.kardashev_min.value <= c.get('kardashev_level', 0.7) <= self.kardashev_max.value]

            display(HTML(f"<h3>Filtered Results: {len(civs)} civilizations</h3>"))

            if civs:
                df = pd.DataFrame(civs)
                display(df)

    def display(self):
        """Display the explorer interface."""
        layout = widgets.VBox([
            widgets.HTML("<h2>Results Explorer</h2>"),
            self.status_filter,
            self.kardashev_min,
            self.kardashev_max,
            self.apply_button,
            self.output
        ])

        display(layout)
        return None


class AnimationBuilder:
    """Widget for creating animations from simulation results."""

    def __init__(self, simulation_data: Optional[Dict[str, Any]] = None):
        """
        Initialize animation builder.

        Args:
            simulation_data: Results from NotebookSimulationRunner
        """
        self.data = simulation_data
        self._create_widgets()

    def _create_widgets(self):
        """Create animation control widgets."""
        self.fps_slider = widgets.IntSlider(
            value=30,
            min=10,
            max=60,
            description='FPS:',
            layout=widgets.Layout(width='400px')
        )

        self.duration_slider = widgets.IntSlider(
            value=60,
            min=10,
            max=300,
            description='Duration (s):',
            layout=widgets.Layout(width='400px')
        )

        self.output_path = widgets.Text(
            value='output/animation.mp4',
            description='Output:',
            layout=widgets.Layout(width='400px')
        )

        self.create_button = widgets.Button(
            description='Create Animation',
            button_style='success'
        )
        self.create_button.on_click(self._create_animation)

        self.output = widgets.Output()

    def _create_animation(self, button):
        """Create timeline animation."""
        with self.output:
            clear_output()

            if self.data is None:
                display(HTML("<p style='color: red;'>No simulation data available</p>"))
                return

            display(HTML("<p>Creating animation...</p>"))

            try:
                # Use existing TimelineAnimator
                from great_silence.visualization import TimelineAnimator

                sim = self.data.get('simulation')
                if sim is None:
                    display(HTML("<p style='color: red;'>No simulation object available</p>"))
                    return

                animator = TimelineAnimator(sim)
                anim = animator.create_animation(save_path=self.output_path.value)

                display(HTML(f"<p style='color: green;'>✓ Animation saved to: {self.output_path.value}</p>"))

            except Exception as e:
                display(HTML(f"<p style='color: red;'>Error: {str(e)}</p>"))

    def display(self):
        """Display animation builder interface."""
        layout = widgets.VBox([
            widgets.HTML("<h2>Animation Builder</h2>"),
            self.fps_slider,
            self.duration_slider,
            self.output_path,
            self.create_button,
            self.output
        ])

        display(layout)
        return None


class Galaxy3DExplorer:
    """
    Interactive widget for exploring 3D galaxy visualization with multi-layer controls.

    Provides checkboxes to toggle visualization layers:
    - Background star field
    - Active civilizations (Kardashev colored)
    - Extinct civilizations
    - Death location markers
    - Hazard events (supernovae, GRBs)
    """

    def __init__(self, runner: NotebookSimulationRunner):
        """
        Initialize 3D explorer widget.

        Args:
            runner: NotebookSimulationRunner with completed simulation
        """
        if runner.simulation is None:
            raise ValueError("Runner must have completed simulation")

        self.runner = runner
        self.current_fig = None
        self._create_widgets()

    def _create_widgets(self):
        """Create control widgets."""
        # Layer toggles
        self.show_stars = widgets.Checkbox(
            value=True,
            description='Show background stars',
            style={'description_width': 'initial'}
        )

        self.show_active = widgets.Checkbox(
            value=True,
            description='Show active civilizations (Kardashev colored)',
            style={'description_width': 'initial'}
        )

        self.show_extinct = widgets.Checkbox(
            value=True,
            description='Show extinct civilizations',
            style={'description_width': 'initial'}
        )

        self.show_deaths = widgets.Checkbox(
            value=False,
            description='Show death markers (grouped by cause)',
            style={'description_width': 'initial'}
        )

        self.show_hazards = widgets.Checkbox(
            value=False,
            description='Show hazard events (supernovae, GRBs)',
            style={'description_width': 'initial'}
        )

        self.show_trajectories = widgets.Checkbox(
            value=False,
            description='Show expansion trajectories (parent→colony lines)',
            style={'description_width': 'initial'}
        )

        self.show_spheres = widgets.Checkbox(
            value=False,
            description='Show influence spheres (translucent)',
            style={'description_width': 'initial'}
        )

        # Subsample control
        self.subsample_stars = widgets.IntSlider(
            value=10000,
            min=1000,
            max=100000,
            step=1000,
            description='Star subsample:',
            style={'description_width': '150px'},
            layout=widgets.Layout(width='500px'),
            readout_format=',d'
        )

        # Animation controls
        self.enable_animation = widgets.Checkbox(
            value=False,
            description='Enable Animation (requires snapshots)',
            style={'description_width': 'initial'}
        )

        # Generate button
        self.generate_button = widgets.Button(
            description='Generate Visualization',
            button_style='primary',
            icon='eye',
            layout=widgets.Layout(width='250px', height='40px')
        )
        self.generate_button.on_click(self._on_generate)

        # Animate button
        self.animate_button = widgets.Button(
            description='Create Animation',
            button_style='success',
            icon='play',
            layout=widgets.Layout(width='200px', height='40px')
        )
        self.animate_button.on_click(self._on_animate)

        # Export button
        self.export_button = widgets.Button(
            description='Export to HTML',
            button_style='info',
            icon='download',
            layout=widgets.Layout(width='200px'),
            disabled=True
        )
        self.export_button.on_click(self._on_export)

        self.export_path = widgets.Text(
            value='output/galaxy_3d.html',
            description='Export path:',
            style={'description_width': '100px'},
            layout=widgets.Layout(width='400px')
        )

        # Output area
        self.output = widgets.Output()

    def _on_generate(self, button):
        """Generate visualization with selected layers."""
        with self.output:
            clear_output(wait=True)
            display(HTML("<p>Generating visualization...</p>"))

            try:
                # Create figure with selected layers
                self.current_fig = self.runner.plot_interactive_3d_galaxy(
                    subsample_stars=self.subsample_stars.value,
                    show_stars=self.show_stars.value,
                    show_active=self.show_active.value,
                    show_extinct=self.show_extinct.value,
                    show_deaths=self.show_deaths.value,
                    show_hazards=self.show_hazards.value,
                    show_trajectories=self.show_trajectories.value,
                    show_spheres=self.show_spheres.value
                )

                # Display figure
                clear_output(wait=True)
                display(self.current_fig)

                # Enable export button
                self.export_button.disabled = False

                # Show layer info
                active_layers = []
                if self.show_stars.value:
                    active_layers.append(f"Stars ({self.subsample_stars.value:,})")
                if self.show_active.value:
                    active_layers.append("Active civilizations")
                if self.show_extinct.value:
                    active_layers.append("Extinct civilizations")
                if self.show_deaths.value:
                    active_layers.append("Death markers")
                if self.show_hazards.value:
                    active_layers.append("Hazard events")
                if self.show_trajectories.value:
                    active_layers.append("Expansion trajectories")
                if self.show_spheres.value:
                    active_layers.append("Influence spheres")

                display(HTML(f"<p style='color: green;'>✓ Active layers: {', '.join(active_layers)}</p>"))

            except Exception as e:
                clear_output()
                display(HTML(f"<p style='color: red;'><b>Error:</b> {str(e)}</p>"))

    def _on_export(self, button):
        """Export current figure to HTML."""
        if self.current_fig is None:
            with self.output:
                display(HTML("<p style='color: orange;'>⚠ Generate visualization first</p>"))
            return

        try:
            path = export_interactive_plot(self.current_fig, self.export_path.value, auto_open=False)
            with self.output:
                display(HTML(f"<p style='color: green;'>✓ Exported to: {path}</p>"))
        except Exception as e:
            with self.output:
                display(HTML(f"<p style='color: red;'><b>Export failed:</b> {str(e)}</p>"))

    def _on_animate(self, button):
        """Create animated visualization with time slider."""
        with self.output:
            clear_output(wait=True)

            if not self.enable_animation.value:
                display(HTML("<p style='color: orange;'>⚠ Enable animation checkbox first</p>"))
                return

            display(HTML("<p>Creating animation... (this may take a moment)</p>"))

            try:
                # Create animated figure
                self.current_fig = self.runner.plot_animated_3d_galaxy(
                    subsample_stars=self.subsample_stars.value,
                    show_stars=self.show_stars.value,
                    show_hazards=self.show_hazards.value,
                    show_trajectories=self.show_trajectories.value,
                    show_spheres=self.show_spheres.value
                )

                # Display figure
                clear_output(wait=True)
                display(self.current_fig)

                # Enable export button
                self.export_button.disabled = False

                # Show info
                info_parts = ["<p style='color: green;'>✓ Animation created!</p>"]
                if self.show_trajectories.value or self.show_spheres.value:
                    info_parts.append("<p><i>Note: Trajectories and spheres grow over time as civilizations expand</i></p>")
                info_parts.append("<p><b>Controls:</b> Use Play/Pause buttons and timeline slider to explore simulation evolution</p>")

                display(HTML(''.join(info_parts)))

            except ValueError as e:
                clear_output()
                display(HTML(
                    f"<p style='color: red;'><b>Error:</b> {str(e)}</p>"
                    "<p>Make sure your simulation was run with snapshots enabled:</p>"
                    "<pre>config.simulation.save_snapshots = True</pre>"
                ))
            except Exception as e:
                clear_output()
                display(HTML(f"<p style='color: red;'><b>Error:</b> {str(e)}</p>"))

    def display(self):
        """Display the 3D explorer interface."""
        # Layer controls section
        layer_controls = widgets.VBox([
            widgets.HTML("<h3>Visualization Layers</h3>"),
            self.show_stars,
            self.show_active,
            self.show_extinct,
            self.show_deaths,
            self.show_hazards,
            self.show_trajectories,
            self.show_spheres,
        ])

        # Settings section
        settings = widgets.VBox([
            widgets.HTML("<br><h3>Settings</h3>"),
            self.subsample_stars,
        ])

        # Animation section
        animation_controls = widgets.VBox([
            widgets.HTML("<br><h3>Animation</h3>"),
            self.enable_animation,
            self.animate_button,
        ])

        # Controls section
        controls = widgets.VBox([
            widgets.HTML("<br>"),
            self.generate_button,
            widgets.HTML("<br><h3>Export</h3>"),
            self.export_path,
            self.export_button,
        ])

        # Main layout
        main_layout = widgets.VBox([
            widgets.HTML("<h2 style='color: #2e86de;'>Interactive 3D Galaxy Explorer</h2>"),
            widgets.HTML("<hr>"),
            layer_controls,
            settings,
            animation_controls,
            controls,
            widgets.HTML("<hr>"),
            self.output
        ], layout=widgets.Layout(padding='20px'))

        display(main_layout)
        return None
