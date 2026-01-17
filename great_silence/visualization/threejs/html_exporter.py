"""HTML export for Three.js visualization."""

from pathlib import Path
from typing import Optional, Union, Any
import json
import numpy as np

from .config import ThreeJSConfig
from .data_extractor import SimulationDataExtractor, StellarKeyframe, EventData


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

    def _load_data(self, animated: bool = False, use_hermite: bool = True):
        """Load and prepare data for template rendering.

        Args:
            animated: Include animation frames
            use_hermite: Use Hermite keyframe interpolation for stellar motion
        """
        import time as time_module
        print(f"[Exporter] Starting _load_data (animated={animated}, use_hermite={use_hermite})", flush=True)
        t0 = time_module.time()
        
        galaxy_data = self.extractor.extract_galaxy_data()
        print(f"[Exporter] extract_galaxy_data: {time_module.time()-t0:.2f}s, {len(galaxy_data.get('positions', []))} positions", flush=True)
        
        t1 = time_module.time()
        hr_data = self.extractor.extract_stellar_hr_data()
        print(f"[Exporter] extract_stellar_hr_data: {time_module.time()-t1:.2f}s", flush=True)
        
        t2 = time_module.time()
        civ_stats = self.extractor.extract_civ_statistics()
        print(f"[Exporter] extract_civ_statistics: {time_module.time()-t2:.2f}s", flush=True)

        if animated:
            time_range = [0, 1]

            if self.extractor.snapshots:
                time_range = [
                    self.extractor.snapshots[0]["time"],
                    self.extractor.snapshots[-1]["time"],
                ]
            print(f"[Exporter] Time range: {time_range[0]:.3f} - {time_range[1]:.3f} Gyr", flush=True)
            
            # Try Hermite keyframe extraction first (memory efficient)
            if use_hermite and self.config.hermite_interpolation:
                print(f"[Exporter] Starting keyframe extraction (max={self.config.max_keyframes})...", flush=True)
                t3 = time_module.time()
                keyframes, event_data = self.extractor.extract_keyframes(
                    max_keyframes=self.config.max_keyframes,
                    include_events=self.config.keyframe_include_events,
                )
                print(f"[Exporter] extract_keyframes: {time_module.time()-t3:.2f}s, {len(keyframes)} keyframes", flush=True)
                
                if len(keyframes) >= 2:
                    # Use new keyframe-based system
                    # Note: keyframes already have subsampled positions, no need to subsample again
                    keyframe_list = [kf.to_dict(None) for kf in keyframes]
                    
                    self.data = {
                        "galaxy": galaxy_data,
                        "keyframes": keyframe_list,
                        "events": event_data.to_dict(),
                        "time_range": time_range,
                        "time_range_myr": [time_range[0] * 1000, time_range[1] * 1000],
                        "hr_data": hr_data,
                        "civ_stats": civ_stats,
                        "use_hermite": True,
                    }
                    
                    # Also create legacy frames for backwards compatibility
                    frames = self._create_frames_from_events(event_data, time_range)
                    frames_json = json.dumps(frames)
                    
                    keyframe_json = json.dumps({
                        "keyframes": keyframe_list,
                        "events": event_data.to_dict(),
                        "time_range_myr": [time_range[0] * 1000, time_range[1] * 1000],
                    })
                    
                    self.data["frames"] = frames
                    self.data["animation_data"] = frames_json
                    self.data["keyframe_data"] = keyframe_json
                    
                    keyframe_size_mb = len(keyframe_json) / (1024 * 1024)
                    frames_size_mb = len(frames_json) / (1024 * 1024)
                    self.data["animation_data_size_mb"] = frames_size_mb
                    self.data["keyframe_data_size_mb"] = keyframe_size_mb
                    
                    # Track all data sizes
                    hr_data_json = json.dumps(hr_data)
                    civ_stats_json = json.dumps(civ_stats)
                    galaxy_json = json.dumps(galaxy_data)
                    hr_size_mb = len(hr_data_json) / (1024 * 1024)
                    civ_stats_size_mb = len(civ_stats_json) / (1024 * 1024)
                    galaxy_size_mb = len(galaxy_json) / (1024 * 1024)
                    
                    print(f"[Hermite] Using {len(keyframes)} keyframes ({keyframe_size_mb:.2f} MB)")
                    print(f"[Hermite] Legacy frames: {len(frames)} ({frames_size_mb:.2f} MB)")
                    print(f"[Hermite] HR data: {hr_size_mb:.2f} MB ({len(hr_data.get('per_frame', []))} frames)")
                    print(f"[Hermite] Civ stats: {civ_stats_size_mb:.2f} MB")
                    print(f"[Hermite] Galaxy data: {galaxy_size_mb:.2f} MB")
                    
                    total_embedded = hr_size_mb + civ_stats_size_mb + galaxy_size_mb
                    print(f"[Hermite] Total embedded data: {total_embedded:.2f} MB")
                    
                    # Store JSON for potential external export
                    self.data["hr_data_json"] = hr_data_json
                    self.data["hr_data_size_mb"] = hr_size_mb
                    
                    return
            
            # Fall back to legacy frame-by-frame extraction
            frames = []
            
            if self.extractor.snapshots:
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
                    # Apply same subsampling as galaxy data for consistency
                    if "stellar_positions" in snapshot and snapshot["stellar_positions"]:
                        positions = snapshot["stellar_positions"]
                        if hasattr(self.extractor, '_subsample_indices') and self.extractor._subsample_indices is not None:
                            pos_array = np.array(positions)
                            positions = pos_array[self.extractor._subsample_indices].tolist()
                        frame_data["stellar_positions"] = positions
                    frames.append(frame_data)

            self.data = {
                "galaxy": galaxy_data,
                "frames": frames,
                "time_range": time_range,
                "hr_data": hr_data,
                "civ_stats": civ_stats,
                "use_hermite": False,
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
    
    def _create_frames_from_events(self, event_data: EventData, time_range: list) -> list:
        """Create animation frames from sparse event data.
        
        This generates frames at regular intervals, populating them with
        civilization and disaster states derived from the event timeline.
        """
        frames = []
        
        # Collect all unique times from events
        all_times = set()
        for birth in event_data.civ_births:
            all_times.add(birth['time_myr'])
        for death in event_data.civ_deaths:
            all_times.add(death['time_myr'])
        for disaster in event_data.disasters:
            all_times.add(disaster['time_myr'])
        for update in event_data.civ_updates:
            all_times.add(update['time_myr'])
        
        # Add start and end times
        time_range_myr = [time_range[0] * 1000, time_range[1] * 1000]
        all_times.add(time_range_myr[0])
        all_times.add(time_range_myr[1])
        
        # Generate frames at key times
        sorted_times = sorted(all_times)
        
        # Track civilization states
        active_civs = {}  # civ_id -> {star_idx, kardashev, birth_time}
        dead_civs = set()
        
        for time_myr in sorted_times:
            time_gyr = time_myr / 1000.0
            
            # Process births up to this time
            for birth in event_data.civ_births:
                if birth['time_myr'] <= time_myr and birth['civ_id'] not in active_civs and birth['civ_id'] not in dead_civs:
                    active_civs[birth['civ_id']] = {
                        'star_idx': birth['star_idx'],
                        'kardashev': birth['kardashev'],
                        'birth_time': birth['time_myr'],
                    }
            
            # Update kardashev values from updates
            for update in event_data.civ_updates:
                if update['civ_id'] in active_civs and update['time_myr'] <= time_myr:
                    active_civs[update['civ_id']]['kardashev'] = update['kardashev']
            
            # Process deaths up to this time
            for death in event_data.civ_deaths:
                if death['time_myr'] <= time_myr and death['civ_id'] in active_civs:
                    dead_civs.add(death['civ_id'])
                    del active_civs[death['civ_id']]
            
            # Build civilization list for this frame
            civs = []
            for civ_id, state in active_civs.items():
                civs.append({
                    'civ_id': civ_id,
                    'star_idx': state['star_idx'],
                    'kardashev': state['kardashev'],
                    'is_active': True,
                    'age': (time_myr - state['birth_time']) / 1000.0,
                    'position': [0, 0, 0],  # Will be computed via Hermite
                })
            
            # Collect hazards at this time and convert field names for UI compatibility
            hazards = []
            for h in event_data.disasters:
                if abs(h['time_myr'] - time_myr) < 50:
                    hazards.append({
                        'time': h['time_myr'] / 1000.0,  # Convert to Gyr for UI
                        'type': h.get('type', 'unknown'),
                        'position': h.get('position', [0, 0, 0]),
                        'lethal_radius': h.get('lethal_radius_kpc', h.get('lethal_radius', 0.01)),
                        'sterilization_radius': h.get('sterilization_radius_kpc', h.get('lethal_radius_kpc', 0.03)),
                        'energy': h.get('energy', 1e51),
                        'jet_theta': h.get('jet_theta'),
                        'jet_phi': h.get('jet_phi'),
                        'affected_civs': h.get('affected_civs', []),
                    })
            
            # Collect probes at this time
            probes = [p for p in event_data.probes if abs(p['time_myr'] - time_myr) < 50]
            
            # Collect trajectories up to this time
            trajectories = [t for t in event_data.trajectories if t['time_myr'] <= time_myr]
            
            frames.append({
                'time': time_gyr,
                'time_myr': time_myr,
                'civilizations': civs,
                'hazards': hazards,
                'probes': probes,
                'trajectories': trajectories,
            })
        
        return frames

    def render(
        self,
        animated: bool = False,
        show_trajectories: bool = True,
        show_spheres: bool = True,
        show_hazards: bool = True,
        animation_data_url: Optional[str] = None,
        keyframe_data_url: Optional[str] = None,
    ) -> str:
        """Render visualization to HTML string.

        Args:
            animated: Include animation support
            show_trajectories: Show civilization trajectories
            show_spheres: Show expansion spheres
            show_hazards: Show disaster markers
            animation_data_url: External URL for animation data
            keyframe_data_url: External URL for keyframe data

        Returns:
            HTML string
        """
        self._load_data(animated)

        # Don't pass large data to template if using external URLs (avoids double-embedding)
        keyframe_size = self.data.get("keyframe_data_size_mb", 0)
        animation_size = self.data.get("animation_data_size_mb", 0)
        
        # Only embed if small enough AND no external URL
        embed_keyframes = keyframe_size <= self.config.data_embed_threshold_mb and keyframe_data_url is None
        embed_animation = animation_size <= self.config.data_embed_threshold_mb and animation_data_url is None
        
        template_data = {
            "config": self.config.to_dict(),
            "show_trajectories": show_trajectories,
            "show_spheres": show_spheres,
            "show_hazards": show_hazards,
            "animated": animated,
            "animation_data_url": animation_data_url,
            "keyframe_data_url": keyframe_data_url,
            "data": self.data,
            "animation_data": self.data.get("animation_data") if animated and embed_animation else None,
            "keyframe_data": self.data.get("keyframe_data") if animated and embed_keyframes else None,
            "use_hermite": self.data.get("use_hermite", False),
        }

        template = self._get_template()

        html = template.render(**template_data)

        if animated:
            data_placeholder = "<!-- ANIMATION_DATA -->"
            keyframe_placeholder = "<!-- KEYFRAME_DATA -->"
            
            # Handle keyframe data
            if "keyframe_data" in self.data and self.data.get("use_hermite"):
                keyframe_size = self.data.get("keyframe_data_size_mb", 0)
                if keyframe_size <= self.config.data_embed_threshold_mb and keyframe_data_url is None:
                    html = html.replace(
                        keyframe_placeholder,
                        f'<script>window.keyframeData = {self.data["keyframe_data"]};</script>',
                    )
                elif keyframe_data_url:
                    # Load external JSON via fetch, not script tag
                    # The init function will wait for this data
                    fetch_script = f'''<script>
window.keyframeDataUrl = "{keyframe_data_url}";
window.keyframeDataPromise = fetch("{keyframe_data_url}")
    .then(response => response.json())
    .then(data => {{ window.keyframeData = data; return data; }})
    .catch(err => console.error("Failed to load keyframe data:", err));
</script>'''
                    html = html.replace(keyframe_placeholder, fetch_script)
            
            # Handle animation data (legacy frames)
            if "animation_data" in self.data:
                data_size = self.data.get("animation_data_size_mb", 0)

                if (
                    data_size <= self.config.data_embed_threshold_mb
                    and animation_data_url is None
                ):
                    html = html.replace(
                        data_placeholder,
                        f'<script>window.animationData = {{"frames": {self.data["animation_data"]}, "time_range": {json.dumps(self.data.get("time_range", [0, 1]))}}};</script>',
                    )
                elif animation_data_url:
                    # Load external JSON via fetch, not script tag
                    fetch_script = f'''<script>
window.animationDataUrl = "{animation_data_url}";
window.animationDataPromise = fetch("{animation_data_url}")
    .then(response => response.json())
    .then(data => {{ window.animationData = {{"frames": data, "time_range": {json.dumps(self.data.get("time_range", [0, 1]))}}}; return data; }})
    .catch(err => console.error("Failed to load animation data:", err));
</script>'''
                    html = html.replace(data_placeholder, fetch_script)

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
        import time as time_module
        print(f"[Exporter] export() called, filepath={filepath}", flush=True)
        t0 = time_module.time()
        
        self._load_data(animated)
        print(f"[Exporter] _load_data completed in {time_module.time()-t0:.2f}s", flush=True)

        t1 = time_module.time()
        template_data = {
            "config": self.config.to_dict(),
            "show_trajectories": show_trajectories,
            "show_spheres": show_spheres,
            "show_hazards": show_hazards,
            "animated": animated,
            "data": self.data,
            "animation_data": self.data.get("animation_data") if animated else None,
            "keyframe_data": self.data.get("keyframe_data") if animated else None,
            "use_hermite": self.data.get("use_hermite", False),
        }

        template = self._get_template()
        print(f"[Exporter] Rendering template...", flush=True)

        html = template.render(**template_data)
        print(f"[Exporter] Template rendered in {time_module.time()-t1:.2f}s, size={len(html)/(1024*1024):.2f}MB", flush=True)

        animation_data_url = None
        keyframe_data_url = None
        
        if animated:
            # Handle keyframe data export (if using Hermite)
            if "keyframe_data" in self.data and self.data.get("use_hermite"):
                keyframe_size = self.data.get("keyframe_data_size_mb", 0)
                if keyframe_size > self.config.data_embed_threshold_mb:
                    keyframe_filename = Path(filepath).stem + "_keyframes.json"
                    keyframe_filepath = Path(filepath).parent / keyframe_filename
                    keyframe_data_url = keyframe_filename
                    
                    print(f"[Exporter] Writing external keyframes: {keyframe_filepath} ({keyframe_size:.2f} MB)", flush=True)
                    with open(keyframe_filepath, "w") as f:
                        f.write(self.data["keyframe_data"])
            
            # Handle animation data export
            if "animation_data" in self.data:
                data_size = self.data.get("animation_data_size_mb", 0)

                if data_size > self.config.data_embed_threshold_mb:
                    data_filename = Path(filepath).stem + "_data.json"
                    data_filepath = Path(filepath).parent / data_filename
                    animation_data_url = data_filename

                    print(f"[Exporter] Writing external animation data: {data_filepath} ({data_size:.2f} MB)", flush=True)
                    with open(data_filepath, "w") as f:
                        f.write(self.data["animation_data"])

        print(f"[Exporter] render() for final HTML...", flush=True)
        t2 = time_module.time()
        html = self.render(
            animated=animated,
            show_trajectories=show_trajectories,
            show_spheres=show_spheres,
            show_hazards=show_hazards,
            animation_data_url=animation_data_url,
            keyframe_data_url=keyframe_data_url,
        )
        print(f"[Exporter] render() completed in {time_module.time()-t2:.2f}s, HTML={len(html)/(1024*1024):.2f}MB", flush=True)

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"[Exporter] Writing HTML to {filepath}...", flush=True)
        t3 = time_module.time()
        if compress:
            import gzip
            
            with gzip.open(str(filepath) + ".gz", "wb") as f:
                f.write(html.encode("utf-8"))
        else:
            with open(filepath, "w") as f:
                f.write(html)
        print(f"[Exporter] HTML written in {time_module.time()-t3:.2f}s", flush=True)
        
        from jinja2 import Environment, FileSystemLoader
        import great_silence.visualization.threejs.templates as templates_pkg
        
        templates_dir = Path(templates_pkg.__file__).parent
        env = Environment(loader=FileSystemLoader(templates_dir))
        js_template_files = list(templates_dir.glob("*.js.j2"))
        print(f"[Exporter] Rendering {len(js_template_files)} JS templates...", flush=True)
        t4 = time_module.time()
        
        for template_file in js_template_files:
            template = env.get_template(template_file.name)
            js_content = template.render(**template_data)
            
            js_filename = template_file.stem.replace('.js', '') + '.js'
            js_filepath = filepath.parent / js_filename
            
            with open(js_filepath, "w") as jf:
                jf.write(js_content)
        print(f"[Exporter] JS templates written in {time_module.time()-t4:.2f}s", flush=True)
        print(f"[Exporter] export() total time: {time_module.time()-t0:.2f}s", flush=True)

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
