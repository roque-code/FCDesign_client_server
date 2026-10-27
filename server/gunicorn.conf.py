import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

bind = "0.0.0.0:8000"
workers = 2
worker_class = "gevent"
worker_connections = 1000
timeout = 0
accesslog = "-"
errorlog = "-"


def on_starting(server):
    """Un proceso aparte guarda la sesión del lenguaje entre workers."""
    token = secrets.token_hex(16)
    path = Path("/tmp/traza-language.token")
    path.write_text(token, encoding="utf-8")
    path.chmod(0o600)
    os.environ["TRAZA_LANGUAGE_TOKEN"] = token
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        subprocess.Popen(
            [sys.executable, "-m", "local_host.browser_host"],
            cwd=root,
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        server.log.exception("No se pudo arrancar el host de lenguajes.")
        return
    port = int(os.environ.get("TRAZA_LANGUAGE_PORT", "8766"))
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), 0.2):
                server.log.info("El host de lenguajes escucha en 127.0.0.1:%s.", port)
                return
        except OSError:
            time.sleep(0.1)
    server.log.error("El host de lenguajes no abrió el puerto.")
