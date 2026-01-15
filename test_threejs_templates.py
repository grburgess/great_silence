"""Test Three.js templates with mock data."""

from pathlib import Path
from great_silence.visualization.threejs.mock_data_generator import generate_mock_data
from great_silence.visualization.threejs.html_exporter import ThreeJSRenderer, ThreeJSConfig
from jinja2 import Template
import json

def test_templates():
    """Test template rendering with mock data."""
    print("Generating mock data...")
    mock_data = generate_mock_data(num_stars=1000, num_frames=50, seed=42)

    print(f"  Galaxy: {len(mock_data['galaxy']['positions'])} stars")
    print(f"  Frames: {len(mock_data['frames'])}")
    print(f"  Camera presets: {len(mock_data['camera_presets'])}")

    output_path = Path("output/test_threejs_mock.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\nLoading templates...")
    template_dir = Path("great_silence/visualization/threejs/templates")
    
    with open(template_dir / "index.html.j2", 'r') as f:
        index_template = Template(f.read())
    
    print(f"  Loaded index.html.j2")

    print(f"\nPreparing template data...")
    config = ThreeJSConfig()
    
    frames_json = json.dumps(mock_data['frames'])
    frames_size_mb = len(frames_json) / (1024 * 1024)
    
    template_data = {
        "config": config.to_dict(),
        "show_trajectories": True,
        "show_spheres": True,
        "show_hazards": True,
        "animated": True,
        "animation_data_url": None,
    }
    
    template_data.update(mock_data)
    template_data["animation_data"] = frames_json

    print(f"  Animation data size: {frames_size_mb:.2f} MB")

    print(f"\nRendering HTML...")
    html = index_template.render(**template_data)

    with open(output_path, 'w') as f:
        f.write(html)

    print(f"  Saved to: {output_path}")
    print(f"  File size: {output_path.stat().st_size / 1024:.1f} KB")

    print("\n✓ Template rendering complete!")
    print(f"\nOpen in browser: file://{output_path.absolute()}")
    print("\nExpected features:")
    print("  - Star particle system with custom shaders")
    print("  - Civilization sprites colored by Kardashev scale")
    print("  - Probe trails")
    print("  - Hazard markers (supernovae, GRBs)")
    print("  - Timeline scrubbing")
    print("  - Playback controls (play/pause, step, reset)")
    print("  - Speed control (0.1x - 10x)")
    print("  - Layer toggles (stars, civilizations, probes, hazards)")
    print("  - Camera presets (Top, Edge, Angled)")
    print("  - Auto-rotate mode")
    print("  - Keyboard controls (WASD, arrows, +/-, Space)")
    print("  - Info panel on hover over civilizations")
    print("  - Mini-map")
    print("  - Export frame button")
    print("  - Post-processing toggle (bloom, film grain, vignette)")

if __name__ == "__main__":
    test_templates()
