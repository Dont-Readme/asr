from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run summary API")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8093)
    parser.add_argument("--reload", action="store_true")
    return parser.parse_args()


def main() -> int:
    try:
        import uvicorn
    except ImportError as error:
        raise SystemExit(f"FastAPI server dependencies are missing: {error}") from error

    args = parse_args()
    uvicorn.run("src.api.summarize_app:create_app", host=args.host, port=args.port, reload=args.reload, factory=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
