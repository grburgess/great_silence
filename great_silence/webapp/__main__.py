"""CLI entry point for the Great Silence webapp."""

import argparse
from .app import run_app


def main():
    parser = argparse.ArgumentParser(
        description="Launch the Great Silence web application"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to listen on (default: 8080)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()
    run_app(host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
