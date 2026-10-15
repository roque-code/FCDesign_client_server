"""Arranca el intérprete local y anuncia el origen por la salida estándar."""

from __future__ import annotations

import argparse
import json
import secrets
import sys

from local_host.serve import LocalServer


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Intérprete local de Traza")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--token", default="")
    parser.add_argument("--api", default="http://127.0.0.1:8002")
    args = parser.parse_args(argv)
    if args.host not in {"127.0.0.1", "localhost"}:
        print("El intérprete local solo escucha en esta máquina.", file=sys.stderr)
        raise SystemExit(2)
    token = args.token or secrets.token_urlsafe(24)
    server = LocalServer((args.host, args.port), token, args.api)
    bound = server.server_address
    raw_host = bound[0]
    host = raw_host.decode("ascii") if isinstance(raw_host, bytes) else str(raw_host)
    port = bound[1]
    origin = f"http://{host}:{port}"
    sys.stdout.write(json.dumps({"origin": origin, "token": token}, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
