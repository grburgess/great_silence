"""Rendered-template hygiene checks for the WebGL fallback renderer."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from great_silence.visualization.threejs.config import ThreeJSConfig

TEMPLATE_DIR = (
    Path(__file__).parent.parent / "great_silence" / "visualization" / "threejs" / "templates"
)


def _render(name):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    return env.get_template(name).render(
        config=ThreeJSConfig().to_dict(),
        show_trajectories=True,
        show_spheres=True,
        show_hazards=True,
        animated=True,
        animation_data_url=None,
        data={},
        animation_data=None,
    )


def test_playback_gates_on_frame_change():
    js = _render("ui.js.j2")
    assert "_lastRenderedFrame" in js


def test_no_per_frame_debug_logging_in_scene():
    js = _render("scene.js.j2")
    assert "[StellarMotion]" not in js
    assert "[Animation]" not in js
    assert "computeBoundingSphere" not in js


def test_scene_has_no_shadowed_playback_impl():
    js = _render("scene.js.j2")
    assert "function initAnimation" not in js
    assert "function playAnimation" not in js
    assert "function stepAnimation" not in js
    assert "function updateAnimation" not in js


def test_civ_sprite_materials_are_cached():
    js = _render("particles.js.j2")
    assert "_civSpriteMaterialCache" in js


def test_teardown_disposes_gpu_resources():
    js = _render("particles.js.j2")
    assert js.count(".dispose()") >= 6


def test_dead_trail_template_removed():
    assert not (TEMPLATE_DIR / "animation.js.j2").exists()
