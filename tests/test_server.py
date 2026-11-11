"""Run the actual Uvicorn process over loopback against an isolated test schema."""

import os
import socket
import subprocess
import sys
import time

import httpx
from sqlalchemy import text


def test_real_uvicorn_startup_readiness_and_auth(database, keys, tmp_path):
    engine, _ = database
    _, public = keys
    with engine.connect() as connection:
        schema = connection.scalar(text("SELECT current_schema()"))
    url = engine.url.update_query_dict({"options": f"-csearch_path={schema}"})
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = {
        **os.environ,
        "ATELIER_DATABASE_URL": url.render_as_string(hide_password=False),
        "ATELIER_JWT_PUBLIC_KEY": public,
        "ATELIER_JWT_ISSUER": "https://synthetic",
        "ATELIER_JWT_AUDIENCE": "atelier-smoke",
        "ATELIER_ALLOWED_HOSTS": '["127.0.0.1"]',
    }
    with (tmp_path / "server.log").open("w+") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "apps.api.main:build_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            env=env,
            stdout=log,
            stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            with httpx.Client(
                base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=1
            ) as client:
                deadline = time.monotonic() + 15
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise AssertionError("Uvicorn exited before becoming ready")
                    try:
                        response = client.get("/health/ready")
                        if response.status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(0.05)
                else:
                    raise AssertionError("Uvicorn readiness timed out")
                assert response.json() == {"status": "ready"}
                assert client.get("/v1/projects").status_code == 401
                assert client.get("/openapi.json").json()["info"]["title"] == "AtelierOS API"
        finally:
            process.terminate()
            process.wait(timeout=10)
