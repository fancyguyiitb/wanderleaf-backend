#!/usr/bin/env python
"""Run the Django development server."""
import os
import shutil
import sys
import atexit
import socket
import subprocess
from urllib.parse import urlparse
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
os.environ.setdefault("DJANGO_ENV", "development")


def _tcp_ping(host: str, port: int, timeout_s: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _parse_redis_host_port(redis_url: str) -> tuple[str, int]:
    """
    Parses redis://host:port/db or rediss://host:port/db.
    Defaults to localhost:6379 if parsing fails.
    """
    try:
        u = urlparse(redis_url)
        host = u.hostname or "localhost"
        port = int(u.port or 6379)
        return host, port
    except Exception:
        return "localhost", 6379


def _try_docker_redis(host: str, port: int) -> bool:
    """Try to start Redis via Docker. Returns True if Redis is reachable after."""
    if shutil.which("docker") is None:
        return False
    try:
        r = subprocess.run(
            ["docker", "start", "wanderleaf-redis"],
            capture_output=True,
            timeout=5,
        )
        if r.returncode != 0:
            # Container may not exist; create it
            subprocess.run(
                [
                    "docker", "run", "-d",
                    "-p", f"{port}:6379",
                    "--name", "wanderleaf-redis",
                    "redis:alpine",
                ],
                capture_output=True,
                timeout=15,
                check=True,
            )
    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False
    for _ in range(25):
        if _tcp_ping(host, port):
            return True
    return False


def ensure_redis_running() -> None:
    """
    Best-effort: start a local Redis for Celery if it isn't running.

    Tries (in order): redis-server in PATH, Docker redis:alpine.
    Only for local development.
    """
    # Never auto-start Redis in production deployments.
    if os.getenv("DJANGO_ENV", "development").lower().strip() == "production":
        return

    if os.getenv("AUTO_START_REDIS", "true").lower() not in ("1", "true", "yes", "on"):
        return

    broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    host, port = _parse_redis_host_port(broker)

    if host not in ("localhost", "127.0.0.1"):
        return

    if _tcp_ping(host, port):
        return

    # 1) Try redis-server (or REDIS_SERVER_EXE)
    exe = os.getenv("REDIS_SERVER_EXE", "redis-server")
    try:
        proc = subprocess.Popen(
            [exe, "--port", str(port), "--save", "", "--appendonly", "no"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        atexit.register(lambda: proc.terminate() if proc.poll() is None else None)
        for _ in range(30):
            if _tcp_ping(host, port):
                print(f"[run.py] Started Redis on {host}:{port}")
                return
        print(f"[run.py] Started redis-server, but {host}:{port} did not open in time.")
        return
    except FileNotFoundError:
        pass

    # 2) Fallback: Docker
    if _try_docker_redis(host, port):
        print(f"[run.py] Started Redis via Docker on {host}:{port}")
        return

    print(
        f"[run.py] Redis not running on {host}:{port}.\n"
        "Install Redis, Memurai, or Docker and run: docker run -d -p 6379:6379 redis:alpine"
    )


if __name__ == "__main__":
    ensure_redis_running()
    from django.core.management import execute_from_command_line
    execute_from_command_line([sys.argv[0], "runserver"] + sys.argv[1:])
