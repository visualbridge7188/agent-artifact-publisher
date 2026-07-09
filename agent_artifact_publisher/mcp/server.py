from __future__ import annotations

import argparse
import json


def self_test() -> dict:
    return {"tools": ["publish_artifact"], "status": "ok"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        print(json.dumps(self_test()))
        return 0
    raise SystemExit("MCP runtime adapter not configured. Use publish_artifact_tool() or CLI fallback.")


if __name__ == "__main__":
    raise SystemExit(main())
