"""Mock data generator for Three.js visualization testing."""

import numpy as np
from typing import Dict, List, Any


def generate_mock_data(num_stars: int = 1000, num_frames: int = 50, seed: int = 42) -> Dict[str, Any]:
    """Generate mock simulation data for Three.js template testing.

    Args:
        num_stars: Number of stars to generate
        num_frames: Number of animation frames
        seed: Random seed for reproducibility

    Returns:
        Dict containing galaxy, frames, and camera_presets data
    """
    rng = np.random.default_rng(seed)

    galaxy_data = {
        "positions": _generate_star_positions(num_stars, rng),
        "colors": _generate_star_colors(num_stars, rng),
    }

    frames = _generate_frames(num_frames, galaxy_data["positions"], rng)

    camera_presets = [
        {
            "name": "Galaxy Top",
            "position": [0.0, 0.0, 40.0],
            "target": [0.0, 0.0, 0.0],
            "duration": 2.0,
        },
        {
            "name": "Galaxy Edge",
            "position": [30.0, 0.0, 0.0],
            "target": [0.0, 0.0, 0.0],
            "duration": 2.0,
        },
        {
            "name": "Galaxy Angled",
            "position": [25.0, 25.0, 15.0],
            "target": [0.0, 0.0, 0.0],
            "duration": 2.5,
        },
    ]

    return {
        "galaxy": galaxy_data,
        "frames": frames,
        "camera_presets": camera_presets,
    }


def _generate_star_positions(num_stars: int, rng: np.random.Generator) -> np.ndarray:
    """Generate galaxy-like star positions.

    Args:
        num_stars: Number of stars
        rng: Random number generator

    Returns:
        Array of shape (num_stars, 3) with positions in kpc
    """
    positions = np.zeros((num_stars, 3))

    for i in range(num_stars):
        radius = rng.exponential(3.0)
        angle = rng.uniform(0, 2 * np.pi)
        z_scale = rng.normal(0, 0.3)

        positions[i, 0] = radius * np.cos(angle)
        positions[i, 1] = radius * np.sin(angle)
        positions[i, 2] = radius * z_scale * np.exp(-radius / 10.0)

    return positions


def _generate_star_colors(num_stars: int, rng: np.random.Generator) -> np.ndarray:
    """Generate star colors based on temperature.

    Args:
        num_stars: Number of stars
        rng: Random number generator

    Returns:
        Array of shape (num_stars, 3) with RGB colors
    """
    colors = np.zeros((num_stars, 3))

    for i in range(num_stars):
        temp_factor = rng.uniform(0, 1)

        if temp_factor < 0.3:
            colors[i] = [1.0, 0.9, 0.8]
        elif temp_factor < 0.6:
            colors[i] = [1.0, 1.0, 1.0]
        else:
            colors[i] = [0.8, 0.9, 1.0]

    return colors


def _generate_frames(
    num_frames: int, star_positions: np.ndarray, rng: np.random.Generator
) -> List[Dict[str, Any]]:
    """Generate animation frames.

    Args:
        num_frames: Number of frames
        star_positions: Star positions array
        rng: Random number generator

    Returns:
        List of frame dictionaries
    """
    frames = []
    num_civs = 10
    civ_positions = rng.choice(len(star_positions), num_civs, replace=False)
    civ_kardashev = np.linspace(0.7, 2.5, num_civs)

    for frame_idx in range(num_frames):
        time = frame_idx * 0.1

        civilizations = []
        probes = []
        hazards = []

        for civ_idx in range(num_civs):
            if time >= civ_idx * 0.05:
                pos = star_positions[civ_positions[civ_idx]].tolist()
                civilizations.append(
                    {
                        "civ_id": civ_idx,
                        "position": pos,
                        "kardashev": float(civ_kardashev[civ_idx]),
                        "age": time - civ_idx * 0.05,
                        "is_active": rng.random() > 0.1,
                    }
                )

                if time >= civ_idx * 0.05 + 0.2:
                    probe_pos = [
                        pos[0] + rng.uniform(-2, 2),
                        pos[1] + rng.uniform(-2, 2),
                        pos[2] + rng.uniform(-0.5, 0.5),
                    ]
                    probes.append(
                        {"position": probe_pos, "civ_id": civ_idx, "progress": rng.random()}
                    )

        if frame_idx == 10:
            hazards.append(
                {
                    "position": [10.0, -5.0, 0.0],
                    "type": "supernova",
                    "time": 1.0,
                    "lethal_radius": 5.0,
                }
            )

        if frame_idx == 25:
            hazards.append(
                {
                    "position": [-8.0, 6.0, 1.0],
                    "type": "grb",
                    "time": 2.5,
                    "lethal_radius": 8.0,
                }
            )

        frames.append(
            {
                "time": time,
                "civilizations": civilizations,
                "probes": probes,
                "hazards": hazards,
            }
        )

    return frames


if __name__ == "__main__":
    mock_data = generate_mock_data()
    print(f"Generated mock data with {len(mock_data['frames'])} frames")
    print(f"Galaxy has {len(mock_data['galaxy']['positions'])} stars")
    print(f"Camera presets: {[p['name'] for p in mock_data['camera_presets']]}")
