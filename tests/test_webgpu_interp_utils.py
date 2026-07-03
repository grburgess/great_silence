"""Node-run tests for the WebGPU interpolation helpers."""

import shutil
import subprocess
from pathlib import Path

import pytest

MJS = (
    Path(__file__).parent.parent
    / "great_silence"
    / "visualization"
    / "threejs"
    / "templates"
    / "webgpu"
    / "interp-utils.mjs"
)

NODE_SCRIPT = """
import {{ bracketForTime, lerp3 }} from '{mjs}';

function eq(actual, expected, label) {{
    if (JSON.stringify(actual) !== JSON.stringify(expected)) {{
        console.error(`FAIL ${{label}}: got ${{JSON.stringify(actual)}} expected ${{JSON.stringify(expected)}}`);
        process.exit(1);
    }}
}}

const times = [0, 100, 250, 250.0000001, 500];
eq(bracketForTime(times, -50), {{i: 0, j: 0, alpha: 0}}, 'before-first clamps');
eq(bracketForTime(times, 600), {{i: 4, j: 4, alpha: 0}}, 'after-last clamps');
eq(bracketForTime(times, 100), {{i: 1, j: 2, alpha: 0}}, 'exact keyframe hit');
eq(bracketForTime(times, 175), {{i: 1, j: 2, alpha: 0.5}}, 'midpoint non-uniform');
eq(bracketForTime(times, 250.00000005), {{i: 2, j: 3, alpha: 1}}, 'duplicate-time guard jumps to later frame');
eq(lerp3([0, 0, 0], [2, 4, 6], 0.5), [1, 2, 3], 'lerp3');
console.log('OK');
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_bracket_and_lerp_helpers(tmp_path):
    script = tmp_path / "run.mjs"
    script.write_text(NODE_SCRIPT.format(mjs=MJS.resolve()))
    result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
