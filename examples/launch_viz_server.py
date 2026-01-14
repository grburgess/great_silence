"""Launch local server for Three.js visualization."""

import subprocess
import sys
from pathlib import Path


def launch_server():
    """Start local HTTP server and open browser."""
    examples_dir = Path("examples")
    
    if not examples_dir.exists():
        print("ERROR: examples/ directory not found")
        return

    html_file = examples_dir / "galaxy_visualization.html"
    
    if not html_file.exists():
        print(f"ERROR: {html_file} not found")
        print("  Run 'python examples/quick_viz_example.py' first")
        return

    port = 8080
    url = f"http://localhost:{port}/examples/galaxy_visualization.html"

    print("=" * 80)
    print("THREE.JS VISUALIZATION SERVER")
    print("=" * 80)
    print()
    print(f"  URL: {url}")
    print(f"  Directory: {examples_dir.absolute()}")
    print()
    print("  Press Ctrl+C to stop the server")
    print()
    print("=" * 80)
    print("OPENING IN BROWSER")
    print("=" * 80)
    print()

    if sys.platform == 'darwin':
        subprocess.Popen(['open', url])
    elif sys.platform == 'linux':
        subprocess.Popen(['xdg-open', url])
    elif sys.platform == 'win32':
        subprocess.Popen(['start', url], shell=True)

    print("Starting server...")
    try:
        import http.server
        server = http.server.HTTPServer(('', port), http.server.SimpleHTTPRequestHandler)
        print(f"✓ Server running on port {port}")
        print()
        server.serve_forever()
    except OSError as e:
        print(f"ERROR: {e}")
        print(f"  Try using a different port")


if __name__ == "__main__":
    launch_server()
