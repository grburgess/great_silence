"""HTML export for Three.js visualization."""

from pathlib import Path
from typing import Optional, Union, Any
import json

from .config import ThreeJSConfig
from .data_extractor import SimulationDataExtractor


class ThreeJSRenderer:
    """Render Three.js visualization as self-contained HTML."""

    def __init__(
        self,
        source: Union[str, Path, Any],
        config: Optional[ThreeJSConfig] = None,
        template_dir: Optional[str] = None,
    ):
        """Initialize renderer.

        Args:
            source: HDF5 file path or simulation object
            config: Visualization configuration
            template_dir: Optional path to template directory
        """
        self.source = source
        self.config = config or ThreeJSConfig()
        self.template_dir = template_dir
        self.extractor = SimulationDataExtractor(source, self.config)
        self.data: dict = {}

    def _load_data(self, animated: bool = False):
        """Load and prepare data for template rendering.

        Args:
            animated: Include animation frames
        """
        galaxy_data = self.extractor.extract_galaxy_data()
        
        hr_data = self.extractor.extract_stellar_hr_data()
        civ_stats = self.extractor.extract_civ_statistics()

        if animated:
            frames = []
            time_range = [0, 1]

            if self.extractor.snapshots:
                time_range = [
                    self.extractor.snapshots[0]["time"],
                    self.extractor.snapshots[-1]["time"],
                ]

                for snapshot in self.extractor.snapshots:
                    frame_data = {
                        "time": snapshot["time"],
                        "time_myr": snapshot.get("time_myr", snapshot["time"] * 1000),
                        "civilizations": snapshot.get(
                            "civilizations", []
                        ),
                        "probes": snapshot.get("probes", []),
                        "hazards": snapshot.get("hazards", []),
                        "trajectories": snapshot.get("trajectories", []),
                    }
                    # Include stellar positions if available (for stellar motion)
                    if "stellar_positions" in snapshot and snapshot["stellar_positions"]:
                        frame_data["stellar_positions"] = snapshot["stellar_positions"]
                    frames.append(frame_data)

            self.data = {
                "galaxy": galaxy_data,
                "frames": frames,
                "time_range": time_range,
                "hr_data": hr_data,
                "civ_stats": civ_stats,
            }

            frames_json = json.dumps(frames)
            frames_size_mb = len(frames_json) / (1024 * 1024)
            self.data["animation_data"] = frames_json
            self.data["animation_data_size_mb"] = frames_size_mb

        else:
            civ_data = self.extractor.extract_civilization_data()
            trajectory_data = self.extractor.extract_trajectory_data()
            probe_data = self.extractor.extract_probe_data()
            hazard_data = self.extractor.extract_hazard_data()

            self.data = {
                "galaxy": galaxy_data,
                "civilizations": civ_data,
                "trajectories": trajectory_data,
                "probes": probe_data,
                "hazards": hazard_data,
                "hr_data": hr_data,
                "civ_stats": civ_stats,
            }

    def render(
        self,
        animated: bool = False,
        show_trajectories: bool = True,
        show_spheres: bool = True,
        show_hazards: bool = True,
        animation_data_url: Optional[str] = None,
    ) -> str:
        """Render visualization to HTML string.

        Args:
            animated: Include animation support
            show_trajectories: Show civilization trajectories
            show_spheres: Show expansion spheres
            show_hazards: Show disaster markers
            animation_data_url: External URL for animation data

        Returns:
            HTML string
        """
        self._load_data(animated)

        template_data = {
            "config": self.config.to_dict(),
            "show_trajectories": show_trajectories,
            "show_spheres": show_spheres,
            "show_hazards": show_hazards,
            "animated": animated,
            "animation_data_url": animation_data_url,
            "data": self.data,
            "animation_data": self.data.get("animation_data") if animated else None,
        }

        template = self._get_template()

        html = template.render(**template_data)

        if animated and "animation_data" in self.data:
            data_placeholder = "<!-- ANIMATION_DATA -->"
            data_size = self.data.get(
                "animation_data_size_mb", 0
            )

            if (
                data_size <= self.config.data_embed_threshold_mb
                and animation_data_url is None
            ):
                html = html.replace(
                    data_placeholder,
                    f'<script>window.animationData = {self.data["animation_data"]};</script>',
                )
            elif animation_data_url:
                html = html.replace(
                    data_placeholder,
                    f'<script src="{animation_data_url}"></script>',
                )

        return html

    def export(
        self,
        filepath: Union[str, Path],
        animated: bool = False,
        show_trajectories: bool = True,
        show_spheres: bool = True,
        show_hazards: bool = True,
        compress: bool = False,
    ):
        """Export visualization to HTML file.

        Args:
            filepath: Output HTML file path
            animated: Include animation support
            show_trajectories: Show civilization trajectories
            show_spheres: Show expansion spheres
            show_hazards: Show disaster markers
            compress: Compress output with gzip
        """
        self._load_data(animated)

        template_data = {
            "config": self.config.to_dict(),
            "show_trajectories": show_trajectories,
            "show_spheres": show_spheres,
            "show_hazards": show_hazards,
            "animated": animated,
            "data": self.data,
            "animation_data": self.data.get("animation_data") if animated else None,
        }

        template = self._get_template()

        html = template.render(**template_data)

        animation_data_url = None
        if animated and "animation_data" in self.data:
            data_size = self.data.get(
                "animation_data_size_mb", 0
            )

            if data_size > self.config.data_embed_threshold_mb:
                data_filename = Path(filepath).stem + "_data.json"
                data_filepath = Path(filepath).parent / data_filename
                animation_data_url = data_filename

                with open(data_filepath, "w") as f:
                    f.write(self.data["animation_data"])

        html = self.render(
            animated=animated,
            show_trajectories=show_trajectories,
            show_spheres=show_spheres,
            show_hazards=show_hazards,
            animation_data_url=animation_data_url,
        )

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if compress:
            import gzip
            
            with gzip.open(str(filepath) + ".gz", "wb") as f:
                f.write(html.encode("utf-8"))
        else:
            with open(filepath, "w") as f:
                f.write(html)
        
        from jinja2 import Environment, FileSystemLoader
        import great_silence.visualization.threejs.templates as templates_pkg
        
        templates_dir = Path(templates_pkg.__file__).parent
        env = Environment(loader=FileSystemLoader(templates_dir))
        js_template_files = templates_dir.glob("*.js.j2")
        
        for template_file in js_template_files:
            template = env.get_template(template_file.name)
            js_content = template.render(**template_data)
            
            js_filename = template_file.stem.replace('.js', '') + '.js'
            js_filepath = filepath.parent / js_filename
            
            with open(js_filepath, "w") as jf:
                jf.write(js_content)

    def _get_template(self, template_name="index.html.j2"):
        """Get Jinja2 template for HTML rendering."""
        try:
            from jinja2 import Environment, FileSystemLoader
            
            if self.template_dir:
                env = Environment(
                    loader=FileSystemLoader(self.template_dir)
                )
            else:
                import great_silence.visualization.threejs.templates as templates_pkg
                
                templates_dir = Path(
                    templates_pkg.__file__
                ).parent
                env = Environment(
                    loader=FileSystemLoader(templates_dir)
                )
            
            return env.get_template(template_name)
        
        except ImportError:
            return _BasicTemplate()


def export_html(
    source,
    output_path,
    config=None,
    animated=False,
    show_trajectories=True,
    show_spheres=True,
    show_hazards=True,
    compress=False,
    template_dir=None,
):
    """Convenience function to export HTML.

    Args:
        source: HDF5 file path or simulation object
        output_path: Output HTML file path
        config: Visualization configuration
        animated: Include animation support
        show_trajectories: Show civilization trajectories
        show_spheres: Show expansion spheres
        show_hazards: Show disaster markers
        compress: Compress output with gzip
        template_dir: Optional template directory path
    """
    renderer = ThreeJSRenderer(
        source, config=config, template_dir=template_dir
    )
    renderer.export(
        output_path,
        animated=animated,
        show_trajectories=show_trajectories,
        show_spheres=show_spheres,
        show_hazards=show_hazards,
        compress=compress,
    )


class _BasicTemplate:
    """Fallback basic template when Jinja2 is not available."""

    def render(self, **kwargs):
        config = kwargs.get("config", {})

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Great Silence Visualization</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, minimum-scale=1.0, maximum-scale=1.0">
    <style>
        body {{ margin: 0; overflow: hidden; background: {config.get('background_color', '#000000')}; }}
        canvas {{ display: block; }}
    </style>
</head>
<body>
    <div id="container"></div>
    <script>
        // Basic visualization template - requires Jinja2 for full features
        console.log("Basic template loaded. Install Jinja2 for full features.");
    </script>
</body>
</html>"""
        return html
